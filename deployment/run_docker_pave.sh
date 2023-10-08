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
EXTERNAL_DRIVE="/media/liangchuan/"
# PAVE env vars
XL_VIP_HOME="/data/tools/pave/v2023.1.withOverlay/PAVE360VSI_v2023.1/common/pave360-open_kit_v22.0.1/xl_vip-questa2022.1"
UVMC_HOME="/data/tools/pave/v2023.1.withOverlay/PAVE360VSI_v2023.1/common/pave360-open_kit_v22.0.1/xl_vip-questa2022.1/shared/xl_uvmc/xl-uvmc-2.3"
PAVE360VSI_HOME="/data/tools/pave/v2023.1.withOverlay/PAVE360VSI_v2023.1"
PAVE360VSI_LIBS="/data/tools/pave/v2023.1.withOverlay/PAVE360VSI_v2023.1/lib"
XL_BUILD_PLATFORM="linux64_el30_gnu74"
UVMC_BUILD_PLATFORM="linux64_el30_gnu74"
XL_VIP=${XL_VIP_HOME}/lib/lib_remote
XL_VIP_OBJ=${XL_VIP}/${XL_BUILD_PLATFORM}
UVMC_LIB_OBJ=${UVMC_HOME}/lib/rawc/client/${UVMC_BUILD_PLATFORM}
SOCKET_DOMAIN=AF_UNIX
XL_TLM_SERVER_IP=localhost
SYSTEMC="/data/tools/systemc/systemc-2.3.2"
SYSTEMC_TLM_HOME="/data/tools/systemc/systemc-2.3.2/include"
SYSC_LIB="lib/linux64_el30_gnu74"

docker run \
	-it \
	--gpus all \
	--rm \
	--net=host \
	--privileged \
	--device=/dev/dri \
	--group-add video \
	--shm-size 12G \
	--volume=/tmp/.X11-unix:/tmp/.X11-unix  \
	-v $HOME/Development:/home/$CONTAINER_USER/Development \
        -v ${EXTERNAL_DRIVE}:/root/media:rw \
	-v ${XL_VIP_HOME}/lib:${XL_VIP_HOME}/lib \
	-v ${UVMC_HOME}:${UVMC_HOME} \
	-v ${SYSTEMC}:${SYSTEMC} \
	-v ${PWD}:/tmp/socketPath \
	-v ${PAVE360VSI_HOME}:${PAVE360VSI_HOME} \
	-e PAVE360VSI_LIBS=${PAVE360VSI_LIBS} \
	-e PAVE360VSI_HOME=${PAVE360VSI_HOME} \
	-e XL_VIP_HOME=${XL_VIP_HOME} \
	-e XL_BUILD_PLATFORM=${XL_BUILD_PLATFORM} \
	-e UVMC_HOME=${UVMC_HOME} \
	-e UVMC_BUILD_PLATFORM=${UVMC_BUILD_PLATFORM} \
	-e LD_LIBRARY_PATH=${UVMC_LIB_OBJ}:${XL_VIP_OBJ}:${PAVE360VSI_LIBS}/${UVMC_BUILD_PLATFORM}/remote/rawc \
	-e SOCKET_DOMAIN=${SOCKET_DOMAIN} \
	-e XL_TLM_SERVER_IP=${XL_TLM_SERVER_IP} \
	-e SYSTEMC=${SYSTEMC} \
	-e SYSTEMC_TLM_HOME=${SYSTEMC_TLM_HOME} \
	-e SYSC_LIB=${SYSC_LIB} \
	-e XL_TLM_AF_UNIX_PATH=/tmp/socketPath \
	-w /home/$CONTAINER_USER/Development/mile/deployment  \
	--env="DISPLAY=$DISPLAY" \
	--name $CONTAINER_NAME $IMAGE_NAME /bin/bash
