import os
import torch

from mile.config import get_parser, get_cfg
from mile.constants import BIRDVIEW_COLOURS
from mile.losses import SegmentationLoss, KLLoss, RegressionLoss, SpatialRegressionLoss
from mile.models.mile import Mile
from mile.models.preprocess import PreProcess


def main():
    checkpoint_path = '/home/Development/mile/epoch=0-step=10000-val_throttle_brake=0.12-val_steering=0.02-val_probabilistic=0.04-val_bev_segmentation_1=0.12-val_bev_center_1=0.06-val_bev_offset_1=0.05-val_loss=0.5834.ckpt'
    # checkpoint_path = 'mile.ckpt'
    if os.path.isfile(checkpoint_path):
        checkpoint_all = torch.load(checkpoint_path, map_location='cpu')
        # print("All Checkpoint keys: {}".format(checkpoint_all.keys()))
        optimizer_state = checkpoint_all['optimizer_states']
        # optimizer_state = {key: value for key,
        #                   value in optimizer_state.items()}
        print("optimizer_state len: {}".format(len(optimizer_state)))
        # print("optimizer keys: {}".format(optimizer_state[0]))
        scheduler_state = checkpoint_all['lr_schedulers']
        print("scheduler_state len: {}".format(len(scheduler_state)))
        print("lr_scheduler keys: {}".format(scheduler_state))
        checkpoint = checkpoint_all['state_dict']
        # print("checkpoint keys: {}".format(checkpoint.keys()))
        checkpoint = {key[6:]: value for key,
                      value in checkpoint.items() if key[:5] == 'model'}

        # Model
        args = get_parser().parse_args()
        print(args)
        cfg = get_cfg(args)
        cfg = get_cfg(cfg_dict=cfg.convert_to_dict())
        model = Mile(cfg)

        def add_weight_decay(model, weight_decay=0.01, skip_list=[]):
            no_decay = []
            decay = []
            for name, param in model.named_parameters():
                if not param.requires_grad:
                    continue
                if len(param.shape) == 1 or any(x in name for x in skip_list):
                    no_decay.append(param)
                else:
                    decay.append(param)
            return [
                {'params': no_decay, 'weight_decay': 0.},
                {'params': decay, 'weight_decay': weight_decay},
            ]

        parameters = add_weight_decay(
            model,
            0.01,
            skip_list=['relative_position_bias_table'],
        )
        weight_decay = 0.
        optimizer = torch.optim.AdamW(
            parameters, lr=1e-4, weight_decay=weight_decay)

        # scheduler
        lr_scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=1e-4,
            total_steps=50000,
            pct_start=0.2,
        )
        optimizer.load_state_dict(optimizer_state[0])
        lr_scheduler.load_state_dict(scheduler_state[0])  # 加上这一句就可以了


if __name__ == '__main__':
    main()
