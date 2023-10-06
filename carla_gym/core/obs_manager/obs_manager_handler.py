"""Adapted from https://github.com/zhejz/carla-roach/ CC-BY-NC 4.0 license."""

from importlib import import_module
from gym import spaces
from time import time
from multiprocessing import Process
import threading


def task(obs_dict, ev_id, obs_id, om):
    start_time = time()
    obs_dict[ev_id][obs_id] = om.get_observation()
    end_time = time()
    execution_time = end_time - start_time
    print("\t\t\t--- observation %s took %s seconds ---" %
          (obs_id, execution_time))


def run_in_thread(obs_dict, ev_id, obs_id, om):
    t = threading.Thread(target=task, args=(obs_dict, ev_id, obs_id, om))
    print(f"Created Thread: {t}")
    t.start()
    return t


class ObsManagerHandler(object):

    def __init__(self, obs_configs):
        self._obs_managers = {}
        self._obs_configs = obs_configs
        self._init_obs_managers()

    def get_observation_process(self, timestamp):
        obs_dict = {}

        ev_id = list(self._obs_managers.keys())[0]
        om_dict = list(self._obs_managers.values())[0]
        obs_dict[ev_id] = {}
        # create all tasks
        processes = [Process(target=task, args=(obs_dict, ev_id, obs_id, om))
                     for obs_id, om in om_dict.items()]
        # start all processes
        for process in processes:
            process.start()
        # wait for all processes to complete
        for process in processes:
            process.join()

        return obs_dict

    def get_observation(self, timestamp):
        obs_dict = {}

        ev_id = list(self._obs_managers.keys())[0]
        om_dict = list(self._obs_managers.values())[0]
        obs_dict[ev_id] = {}
        # create all tasks
        threads = []

        for obs_id, om in om_dict.items():
            threads.append(run_in_thread(obs_dict, ev_id, obs_id, om))
        # wait for all processes to complete
        for s in threads:
            s.join()

        return obs_dict

    def get_observation_loop(self, timestamp):
        obs_dict = {}
        for ev_id, om_dict in self._obs_managers.items():
            obs_dict[ev_id] = {}
            for obs_id, om in om_dict.items():
                obs_dict[ev_id][obs_id] = om.get_observation()
        return obs_dict

    def get_observation_map(self, timestamp):
        obs_dict = {}
        for ev_id, om_dict in self._obs_managers.items():
            obs_dict[ev_id] = {}
            observations = list(
                map(lambda x: [x[0], x[1].get_observation()], om_dict.items()))
            for obs_id, obs in observations:
                obs_dict[ev_id][obs_id] = obs
            # for obs_id, om in om_dict.items():
            #    obs_dict[ev_id][obs_id] = om.get_observation()
        return obs_dict

    @property
    def observation_space(self):
        obs_spaces_dict = {}
        for ev_id, om_dict in self._obs_managers.items():
            ev_obs_spaces_dict = {}
            for obs_id, om in om_dict.items():
                ev_obs_spaces_dict[obs_id] = om.obs_space
            obs_spaces_dict[ev_id] = spaces.Dict(ev_obs_spaces_dict)
        return spaces.Dict(obs_spaces_dict)

    def reset(self, ego_vehicles):
        self._init_obs_managers()

        for ev_id, ev_actor in ego_vehicles.items():
            for obs_id, om in self._obs_managers[ev_id].items():
                om.attach_ego_vehicle(ev_actor)

    def clean(self):
        for ev_id, om_dict in self._obs_managers.items():
            for obs_id, om in om_dict.items():
                om.clean()
        self._obs_managers = {}

    def _init_obs_managers(self):
        for ev_id, ev_obs_configs in self._obs_configs.items():
            self._obs_managers[ev_id] = {}
            for obs_id, obs_config in ev_obs_configs.items():
                ObsManager = getattr(import_module(
                    'carla_gym.core.obs_manager.'+obs_config["module"]), 'ObsManager')
                self._obs_managers[ev_id][obs_id] = ObsManager(obs_config)
