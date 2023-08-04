# Check args
if [ "$#" -lt 1 ]; then
  #echo "usage: ./run.sh IMAGE_NAME"
  #return 1
  echo "Using default: bdi/melodic_amd64:latest"
  IMAGE_NAME=bdi/melodic_amd64:latest
else
  IMAGE_NAME=$1
fi

if [ "$#" -eq 2 ]; then
  CONTAINER_NAME=$2
fi

xhost +
EXTERNAL_DRIVE="/media/bditech/"
docker run \
	-it \
	--gpus all \
	--rm \
	--net=host \
	--privileged \
	--device=/dev/dri \
	--group-add video \
	--shm-size 128G \
	--volume=/tmp/.X11-unix:/tmp/.X11-unix  \
	-v $HOME/dev:/home/$CONTAINER_USER/dev \
        -v ${EXTERNAL_DRIVE}:/root/media \
	-w /home/$CONTAINER_USER/dev  \
	--env="DISPLAY=$DISPLAY" \
	--name $CONTAINER_NAME $IMAGE_NAME /bin/bash
