#!/bin/bash
# Adapted from https://github.com/zhejz/carla-roach/ CC-BY-NC 4.0 license.

if [[ $# -ne 3 ]] ; then
    echo 'Please specify the CARLA executable path, the model weights, and the CARLA port.'
    exit 1
fi

CARLA_PATH=$1
CKPT=$2
PORT=$3


#source ~/miniconda3/etc/profile.d/conda.sh
#conda activate mile
#source ~/miniconda3/envs/mile/etc/conda/activate.d/env_vars.sh

python -u inference.py --config-name evaluate carla_sh_path=${CARLA_PATH} agent.mile.ckpt=${CKPT} port=${PORT} +mode='single'


echo "Bash script done."
