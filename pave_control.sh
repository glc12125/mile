CARLA_VERSION="$1"

if [ "$CARLA_VERSION" = "11" ]; then
    python -u pave_automatic_control.py --config-name pave carla_sh_path=/root/media/crucial/carla/CARLA_0.9.11/CarlaUE4.sh agent.mile.ckpt=/home/Development/mile/mile.ckpt port=2000 +mode='single'
fi

if [ "$CARLA_VERSION" = "14" ]; then
    python -u pave_automatic_control.0.9.14.py --config-name pave carla_sh_path=/root/media/crucial/carla/CARLA_0.9.14/CarlaUE4.sh agent.mile.ckpt=/home/Development/mile/mile.ckpt.pt port=2000 +mode='single'
fi

if [ "$CARLA_VERSION" = "14d" ]; then
    python -u pave_automatic_control.0.9.14.py --config-name pave carla_sh_path=/root/media/crucial/carla/CARLA_0.9.14/CarlaUE4.sh agent.mile.ckpt=/home/Development/mile/mile.ckpt port=2000 +mode='single' show_stats=true log_video=true
fi

echo "Bash script done."
