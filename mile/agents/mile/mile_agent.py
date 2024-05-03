"""Adapted from https://github.com/zhejz/carla-roach CC-BY-NC 4.0 license."""

import logging
from collections import deque

import torch
import time
import os
import sys
import importlib
import pathlib

from omegaconf import OmegaConf
from torchmetrics import JaccardIndex
import numpy as np
import cv2

from carla_gym.utils.config_utils import load_entry_point
from mile.constants import CARLA_FPS, DISPLAY_SEGMENTATION
from mile.data.dataset import calculate_geometry_from_config
from mile.data.dataset_utils import preprocess_birdview_and_routemap, preprocess_measurements, calculate_birdview_labels
from mile.config import get_cfg
from mile.models.mile import Mile
from mile.models.preprocess import PreProcess


class MileAgent:
    def __init__(self, path_to_conf_file='config_agent.yaml'):
        self._logger = logging.getLogger(__name__)
        self._render_dict = None
        self._inference_avg_time = 0.0
        self._preprocess_avg_time = 0.0
        self._postprocess_avg_time = 0.0
        self._metrics_avg_time = 0.0
        self._render_avg_time = 0.0
        self._inference_counter = 0
        self._show_stats = False
        self._callbacks = []
        self.setup(path_to_conf_file)

    def setup(self, path_to_conf_file):
        cfg = OmegaConf.load(path_to_conf_file)
        print("cfg for agent: {}".format(cfg))
        # load checkpoint from wandb
        self._ckpt = None

        cfg = OmegaConf.to_container(cfg)
        self._obs_configs = cfg['obs_configs']
        # for debug view
        self._obs_configs['route_plan'] = {
            'module': 'navigation.waypoint_plan', 'steps': 20}
        wrapper_class = load_entry_point(cfg['env_wrapper']['entry_point'])

        # prepare policy
        self._input_buffer_size = 1
        if cfg['ckpt'] is not None:
            # trainer = WorldModelTrainer.load_from_checkpoint(
            #    cfg['ckpt'], pretrained_path=cfg['ckpt'])
            # print(f'Loading world model weights from {cfg["ckpt"]}')
            # self._policy = trainer.to('cuda')
            self._model_cfg = get_cfg()
            self._model_cfg.RECEPTIVE_FIELD = 6
            self._model_cfg.FUTURE_HORIZON = 6
            model = Mile(self._model_cfg)
            model.load_state_dict(torch.load(cfg['ckpt'], map_location='cpu'))
            self._policy = model.to('cuda')
            self._preprocess = PreProcess(self._model_cfg)
            self._preprocess = self._preprocess.to('cuda')
            game_frequency = CARLA_FPS
            model_stride_sec = self._model_cfg.DATASET.STRIDE_SEC
            receptive_field = model.receptive_field
            n_image_per_stride = int(game_frequency * model_stride_sec)

            self._input_buffer_size = (
                receptive_field - 1) * n_image_per_stride + 1
            self._sequence_indices = range(
                0, self._input_buffer_size, n_image_per_stride)

        self._env_wrapper = wrapper_class(cfg=self._model_cfg)

        self._preprocess = self._preprocess.eval()
        self._policy = self._policy.eval()

        self._policy_input_queue = {
            'image': deque(maxlen=self._input_buffer_size),
            'route_map': deque(maxlen=self._input_buffer_size),
            'route_command': deque(maxlen=self._input_buffer_size),
            'gps_vector': deque(maxlen=self._input_buffer_size),
            'route_command_next': deque(maxlen=self._input_buffer_size),
            'gps_vector_next': deque(maxlen=self._input_buffer_size),
            'speed': deque(maxlen=self._input_buffer_size),
            'intrinsics': deque(maxlen=self._input_buffer_size),
            'extrinsics': deque(maxlen=self._input_buffer_size),
            'birdview': deque(maxlen=self._input_buffer_size),
            'birdview_label': deque(maxlen=self._input_buffer_size),
        }
        self._action_queue = deque(maxlen=self._input_buffer_size)
        self._cfg = cfg

        # Custom metrics
        if self._model_cfg.SEMANTIC_SEG.ENABLED and DISPLAY_SEGMENTATION:
            self._iou = JaccardIndex(
                task='multiclass', num_classes=self._model_cfg.SEMANTIC_SEG.N_CHANNELS).cuda()
            self._real_time_iou = JaccardIndex(
                task='multiclass', num_classes=self._model_cfg.SEMANTIC_SEG.N_CHANNELS, compute_on_step=True,
            ).cuda()

        if self._cfg['online_deployment']:
            print('Online deployment')
        else:
            print('Recomputing')

        self._warm_start = 25
        self._initialize_callbacks()

    def _initialize_callbacks(self):
        for callback in self._cfg['callbacks']:
            # callback_paths.append(Path(cfg['callback_path'], callback))
            # Load Publisher
            current_working_dir = pathlib.Path().resolve()
            print("current_working_dir: {}".format(current_working_dir))
            script_path = pathlib.Path(__file__).parent.resolve()
            print("script_path: {}".format(script_path))
            callback_file_path = str(script_path) + "/../../../" + \
                self._cfg['callback_path'] + '/' + callback
            module_name = os.path.basename(callback_file_path).split('.')[0]
            print("callback_file_path: {}".format(callback_file_path))
            sys.path.insert(0, os.path.dirname(callback_file_path))
            print("os.path.dirname(callback_file_path): {}".format(
                os.path.dirname(callback_file_path)))
            module_callback = importlib.import_module(module_name)
            callback_class_name = module_callback.__name__.title().replace('_', '')
            logging.debug("Initialising callback class: {}".format(
                callback_class_name))
            callback_instance = getattr(module_callback, callback_class_name)()
            logging.debug("Finished initialising callback class: {}".format(
                callback_class_name))
            self._callbacks.append(callback_instance)

    def show_stats(self, show_stats=False):
        self._show_stats = show_stats

    def run_step(self, input_data, timestamp):
        start_time = time.time()
        policy_input, gps_vector, gps_vector_next = self.preprocess_data(
            input_data)
        end_time = time.time()
        execution_time = end_time - start_time
        if self._inference_counter >= self._warm_start and self._show_stats:
            print("\t--- Preprocess time %s seconds ---" % (execution_time))
            self._preprocess_avg_time = (
                self._preprocess_avg_time * self._inference_counter + execution_time) / (self._inference_counter + 1)
            print("\t--- AVG Preprocess time %s seconds ---" %
                  (self._preprocess_avg_time))
        # Forward pass
        with torch.no_grad():
            is_dreaming = False
            start_time = time.time()
            if self._cfg['online_deployment']:
                policy_input = self._preprocess(policy_input)
                output = self._policy.deployment_forward(
                    policy_input, is_dreaming=is_dreaming)
            else:
                output = self._policy(policy_input, deployment=True)
            end_time = time.time()
            execution_time = end_time - start_time
            if self._inference_counter >= self._warm_start and self._show_stats:
                print("\t--- Inferencing time %s seconds ---" %
                      (execution_time))
                self._inference_avg_time = (
                    self._inference_avg_time * self._inference_counter + execution_time) / (self._inference_counter + 1)
                print("\t--- AVG Inferencing time %s seconds ---" %
                      (self._inference_avg_time))
            elif self._show_stats:
                print("\t--- Skipping frame %s" % (self._inference_counter))

        start_time = time.time()
        actions = torch.cat(
            [output['throttle_brake'], output['steering']], dim=-1)[0, 0].cpu().numpy()
        control = self._env_wrapper.process_act(actions)

        # Populate action queue
        self._action_queue.append(torch.from_numpy(actions).cuda())
        end_time = time.time()
        execution_time = end_time - start_time
        if self._inference_counter >= self._warm_start and self._show_stats:
            print("\t--- Postprocess time %s seconds ---" % (execution_time))
            self._postprocess_avg_time = (
                self._postprocess_avg_time * self._inference_counter + execution_time) / (self._inference_counter + 1)
            print("\t--- AVG Postprocess time %s seconds ---" %
                  (self._postprocess_avg_time))
        start_time = time.time()
        # Metrics
        # metrics = self.forward_metrics(policy_input, output)
        end_time = time.time()
        execution_time = end_time - start_time
        if self._inference_counter >= self._warm_start and self._show_stats:
            print("\t--- Forward metrics time %s seconds ---" %
                  (execution_time))
            self._metrics_avg_time = (
                self._metrics_avg_time * self._inference_counter + execution_time) / (self._inference_counter + 1)
            print("\t--- AVG Forward metrics time %s seconds ---" %
                  (self._metrics_avg_time))

        start_time = time.time()
        # self.prepare_rendering(policy_input, output,
        #                       metrics, timestamp, is_dreaming)
        self.prepare_rendering(policy_input, output,
                               None, timestamp, is_dreaming)
        end_time = time.time()
        execution_time = end_time - start_time
        if self._inference_counter >= self._warm_start and self._show_stats:
            print("\t--- Prepare rendering time %s seconds ---" %
                  (execution_time))
            self._render_avg_time = (
                self._render_avg_time * self._inference_counter + execution_time) / (self._inference_counter + 1)
            print("\t--- AVG Prepare rendering time %s seconds ---" %
                  (self._render_avg_time))
        self._inference_counter += 1
        return control, gps_vector, gps_vector_next

    def preprocess_data(self, input_data):
        # Fill the input queue with new elements
        self.image = input_data['central_rgb']['data'].transpose((2, 0, 1))

        route_command, gps_vector = preprocess_measurements(
            input_data['gnss']['command'].squeeze(0),
            input_data['gnss']['gnss'],
            input_data['gnss']['target_gps'],
            input_data['gnss']['imu'],
        )
        if self._show_stats:
            print("\t--- preprocess_data: route_command: {}, gps_vector: {}".format(
                route_command, gps_vector))
        route_command_next, gps_vector_next = preprocess_measurements(
            input_data['gnss']['command_next'].squeeze(0),
            input_data['gnss']['gnss'],
            input_data['gnss']['target_gps_next'],
            input_data['gnss']['imu'],
        )
        if self._show_stats:
            print("\t--- preprocess_data: route_command_next: {}, gps_vector_next: {}".format(
                route_command_next, gps_vector_next))

        birdview, route_map = preprocess_birdview_and_routemap(
            torch.from_numpy(input_data['birdview']['masks']).cuda())
        birdview_label = calculate_birdview_labels(
            birdview, birdview.shape[0]).unsqueeze(0)

        # Make route_map an RGB image
        route_map = route_map.unsqueeze(0).expand(3, -1, -1)
        speed = input_data['speed']['forward_speed']
        intrinsics, extrinsics = calculate_geometry_from_config(
            self._model_cfg)

        # Using gpu inputs
        self._policy_input_queue['image'].append(
            torch.from_numpy(self.image.copy()).cuda())
        self._policy_input_queue['route_command'].append(
            torch.from_numpy(route_command).cuda())
        self._policy_input_queue['gps_vector'].append(
            torch.from_numpy(gps_vector).cuda())
        self._policy_input_queue['route_command_next'].append(
            torch.from_numpy(route_command_next).cuda())
        self._policy_input_queue['gps_vector_next'].append(
            torch.from_numpy(gps_vector_next).cuda())
        self._policy_input_queue['route_map'].append(route_map)
        self._policy_input_queue['speed'].append(
            torch.from_numpy(speed).cuda())
        self._policy_input_queue['intrinsics'].append(
            torch.from_numpy(intrinsics).cuda())
        self._policy_input_queue['extrinsics'].append(
            torch.from_numpy(extrinsics).cuda())

        self._policy_input_queue['birdview'].append(birdview)
        self._policy_input_queue['birdview_label'].append(birdview_label)

        for key in self._policy_input_queue.keys():
            while len(self._policy_input_queue[key]) < self._input_buffer_size:
                self._policy_input_queue[key].append(
                    self._policy_input_queue[key][-1])

        if len(self._action_queue) == 0:
            self._action_queue.append(torch.zeros(
                2, device=torch.device('cuda')))
        while len(self._action_queue) < self._input_buffer_size:
            self._action_queue.append(self._action_queue[-1])

        # Prepare model input
        policy_input = {}
        for key in self._policy_input_queue.keys():
            policy_input[key] = torch.stack(
                list(self._policy_input_queue[key]), axis=0).unsqueeze(0).clone()

        action_input = torch.stack(
            list(self._action_queue), axis=0).unsqueeze(0).float()

        # We do not have access to the last action, as it is the one we're going to compute.
        action_input = torch.cat(
            [action_input[:, 1:], torch.zeros_like(action_input[:, -1:])], dim=1)
        policy_input['action'] = action_input

        # Select right elements in the sequence
        for k, v in policy_input.items():
            policy_input[k] = v[:, self._sequence_indices]

        return policy_input, gps_vector, gps_vector_next

    def prepare_rendering(self, policy_input, output, metrics, timestamp, is_dreaming):
        # For rendering
        self._render_dict = {
            'policy_input': policy_input,
            'obs_configs': self._obs_configs,
            'policy_cfg': self._model_cfg,
            'metrics': metrics,
        }

        for k, v in output.items():
            self._render_dict[k] = v

        self._render_dict['timestamp'] = timestamp
        self._render_dict['is_dreaming'] = is_dreaming

        self.supervision_dict = {}

    def reset(self, log_file_path):
        # logger
        self._logger.handlers = []
        self._logger.propagate = False
        self._logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_file_path, mode='w')
        fh.setLevel(logging.DEBUG)
        self._logger.addHandler(fh)

        for v in self._policy_input_queue.values():
            v.clear()

        self._action_queue.clear()

    def render(self, reward_debug, terminal_debug):
        '''
        test render, used in evaluate.py
        '''
        self._render_dict['reward_debug'] = reward_debug
        self._render_dict['terminal_debug'] = terminal_debug
        im_render = self._env_wrapper.im_render(self._render_dict)
        return im_render

    def forward_metrics(self, policy_input, output):
        real_time_metrics = {}
        if self._model_cfg.SEMANTIC_SEG.ENABLED and DISPLAY_SEGMENTATION:
            with torch.no_grad():
                bev_prediction = output['bev_segmentation_1'].detach()
                bev_prediction = torch.argmax(bev_prediction, dim=2)[:, -1]
                bev_label = policy_input['birdview_label'][:, -1, 0]
                self._iou(bev_prediction.view(-1), bev_label.view(-1))

                real_time_metrics['intersection-over-union'] = self._real_time_iou(
                    bev_prediction, bev_label).mean().item()

        return real_time_metrics

    def compute_metrics(self):
        metrics = {}
        if self._model_cfg.SEMANTIC_SEG.ENABLED and DISPLAY_SEGMENTATION:
            scores = self._iou.compute()
            metrics['intersection-over-union'] = scores.item()
            self._iou.reset()
        return metrics

    @property
    def obs_configs(self):
        return self._obs_configs

    def postprocess(self, vehicle_state):
        if len(self._callbacks) == 0:
            pass

        # The channel order for the model is (c, h, w)
        # while the visualisation and carla generates (h, w, c)
        if self.image.shape[2] > 4:
            rendered_image = self.image.transpose((1, 2, 0))

        #cv2.imshow('ADAS view',rendered_image)
        #cv2.waitKey(1)

        if rendered_image.shape[2] == 3:
            # alpha_channel = np.full((240, 480, 1), 100, 'uint8')
            alpha_channel = np.full((600, 960, 1), 100, 'uint8')
            to_send = np.dstack((rendered_image, alpha_channel))
        elif rendered_image.shape[2] == 4:
            to_send = rendered_image
        else:
            logging.error("unexpected size of image: {}".format(
                rendered_image.shape))
            raise

        structured_data = {
            'image': to_send.tobytes(),
            'vehicle_state': vehicle_state
        }

        for callback in self._callbacks:
            callback.publish(structured_data)
