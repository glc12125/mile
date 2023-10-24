import git
import os
import socket
import time

import pytorch_lightning as pl
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
import torch

from mile.config import get_parser, get_cfg
from mile.data.dataset import DataModule
from mile.trainer import WorldModelTrainer


class SaveGitDiffHashCallback(pl.Callback):
    def setup(self, trainer, pl_module, stage):
        repo = git.Repo()
        trainer.git_hash = repo.head.object.hexsha
        trainer.git_diff = repo.git.diff(repo.head.commit.tree)

    def on_save_checkpoint(self, trainer, pl_module, checkpoint):
        checkpoint['world_size'] = trainer.world_size
        checkpoint['git_hash'] = trainer.git_hash
        checkpoint['git_diff'] = trainer.git_diff


def main():
    args = get_parser().parse_args()
    print(args)
    cfg = get_cfg(args)

    data = DataModule(cfg)
    model = WorldModelTrainer(cfg.convert_to_dict())

    if cfg.LOG_DIR == 'tensorboard_logs':
        save_dir = os.path.join(
            cfg.LOG_DIR, time.strftime('%d%B%Yat%H:%M:%S%Z') + '_' + socket.gethostname() + '_' + cfg.TAG
        )
    else:
        save_dir = cfg.LOG_DIR
    logger = pl.loggers.TensorBoardLogger(save_dir=save_dir)

    callbacks = [
        pl.callbacks.ModelSummary(-1),
        SaveGitDiffHashCallback(),
        pl.callbacks.LearningRateMonitor(),
        ModelCheckpoint(
            save_dir, every_n_train_steps=cfg.VAL_CHECK_INTERVAL, filename="{epoch}-{step}-{val_throttle_brake:.2f}-{val_steering:.2f}-{val_probabilistic:.2f}-{val_bev_segmentation_1:.2f}-{val_bev_center_1:.2f}-{val_bev_offset_1:.2f}-{val_loss:.4f}", save_top_k=3, monitor="val_loss", mode="min"
        ),
    ]

    if cfg.LIMIT_VAL_BATCHES in [0, 1]:
        limit_val_batches = float(cfg.LIMIT_VAL_BATCHES)
    else:
        limit_val_batches = cfg.LIMIT_VAL_BATCHES
    if cfg.LIMIT_TRAIN_BATCHES in [0, 1]:
        limit_train_batches = float(cfg.LIMIT_TRAIN_BATCHES)
    else:
        limit_train_batches = cfg.LIMIT_TRAIN_BATCHES

    replace_sampler_ddp = not cfg.SAMPLER.ENABLED
    torch.cuda.empty_cache()
    trainer = pl.Trainer(
        devices=cfg.GPUS,
        accelerator='gpu',
        strategy='ddp',
        precision=cfg.PRECISION,
        sync_batchnorm=True,
        max_epochs=None,
        max_steps=cfg.STEPS,
        callbacks=callbacks,
        logger=logger,
        log_every_n_steps=cfg.LOGGING_INTERVAL,
        val_check_interval=cfg.VAL_CHECK_INTERVAL,
        limit_train_batches=limit_train_batches,
        limit_val_batches=limit_val_batches,
        replace_sampler_ddp=replace_sampler_ddp,
        accumulate_grad_batches=cfg.OPTIMIZER.ACCUMULATE_GRAD_BATCHES,
        num_sanity_val_steps=2,
    )

    if cfg.PRETRAINED.PATH:
        trainer.fit(model, datamodule=data, ckpt_path=cfg.PRETRAINED.PATH)
    else:
        trainer.fit(model, datamodule=data)


if __name__ == '__main__':
    main()
