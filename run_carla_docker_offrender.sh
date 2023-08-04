#/bin/bash

docker run \
    -p 2000-2002:2000-2002 \
    --net=host \
    --privileged \
    --gpus 'all,"capabilities=graphics,utility,display,video,compute"' \
    -e SDL_VIDEODRIVER='offscreen' \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $HOME/.Xauthority:/root/.Xauthority:rw \
    -e XAUTHORITY=/root/.Xauthority \
    -it \
    carlasim/carla:0.9.11 \
    ./CarlaUE4.sh -ResX=800 -ResY=600 -quality-level=Epic -nosound -RenderOffScreen
