#!/bin/bash
# Adapted from https://github.com/zhejz/carla-roach/ CC-BY-NC 4.0 license.

if [[ $# -ne 4 ]] ; then
    echo 'Please specify the CARLA executable path, the folder to save the dataset, the CARLA port, and test suite.'
    exit 1
fi

CARLA_PATH=$1
DATASET_ROOT=$2
PORT=$3
TEST_SUITE=$4

data_collect () {
  python -u data_collect.py --config-name data_collect carla_sh_path=${CARLA_PATH} dataset_root=${DATASET_ROOT} port=${PORT} test_suites=${TEST_SUITE}
}

#source ~/miniconda3/etc/profile.d/conda.sh
source /root/miniconda3/envs/mile/etc/conda/activate.d/env_vars.sh
conda activate mile

# Remove checkpoint files
#rm outputs/port_${PORT}_checkpoint.txt
#rm outputs/port_${PORT}_wb_run_id.txt
#rm outputs/port_${PORT}_ep_stat_buffer_*.json


# Resume benchmark in case carla crashed.
RED=$'\e[0;31m'
NC=$'\e[0m'
PYTHON_RETURN=1
until [ $PYTHON_RETURN == 0 ]; do
  data_collect
  PYTHON_RETURN=$?
  echo "${RED} PYTHON_RETURN=${PYTHON_RETURN}!!! Start Over!!!${NC}" >&2
  sleep 2
done

echo "Bash script done."
