#bash run/inference.sh /root/media/crucial/carla/CARLA_0.9.11/CarlaUE4.sh /home/Development/mile/'mile.ckpt' 2000

python -u pave_automatic_control.py --config-name pave carla_sh_path=/root/media/crucial/carla/CARLA_0.9.11/CarlaUE4.sh agent.mile.ckpt=/home/Development/mile/mile.ckpt port=2000 +mode='single'


echo "Bash script done."
