TESTS = \
    demoCarlaRosGateway

SOCKET_DOMAIN ?= AF_UNIX

CC = gcc
CXX = g++

OPT=-O3

CFLAGS += $(OPT) -fPIC -Wall


# Note: We add '/usr/include/x86_64-linux-gnu' to the INCL path
# below just in case we're building on an Ubuntu host where the
# usual /usr/include/ stuff is in a slightly different place than
# on RHEL/CentOS/SuSE hosts.
INCL = -I/usr/include/x86_64-linux-gnu -Isrc/server -I$(UVMC_HOME)/src/connect/sc -I$(XL_VIP) 

XL_VIP_LIBS = $(XL_VIP_OBJ)/xl_vip_open_kit.so $(XL_VIP_OBJ)/xl_vip_open_kit_extras.so $(XL_VIP_OBJ)/xl_vip_tlm_xactors.so $(XL_VIP_OBJ)/xl_vip_open_kit_stubs.so

XL_VIP_PREBUILT_OBJS = $(XL_VIP_OBJ)/XlEtherPacketSnooper.o

$(info    XL_VIP_LIBS: ${XL_VIP_LIBS})
$(info    XL_VIP_PREBUILT_OBJS: ${XL_VIP_PREBUILT_OBJS})
#----------------------------------------------------
# UVM and UVMC (XL-UVM-Connect) libraries are needed to support
# XLerated and trans-language TLM conduits.
UVMC_LIB_SO = $(UVMC_LIB_OBJ)/uvmc.so $(UVMC_LIB_OBJ)/uvmc_tlm_fabric.so $(UVMC_LIB_OBJ)/uvmc_stubs.so

COBJS=$(CSRCS:%.c=%.o)
CDEPS=$(CSRCS:%.c=%.d)
OBJS=$(SRCS:%.cxx=%.o)
DEPS=$(SRCS:%.cxx=%.d)

%.d: %.c
	rm -f $@
	$(CC) -M $(CFLAGS) $(INCL) -c $< | sed -e 's+^.*\.o: \(.*\).cxx+\1.o: \1.cxx+' > $@

%.o: %.c
	$(CC) $(CFLAGS) $(INCL) -c $< -o $@

%.d: %.cxx
	rm -f $@
	$(CXX) -M $(CFLAGS) $(INCL) -c $< | sed -e 's+^.*\.o: \(.*\).cxx+\1.o: \1.cxx+' > $@

%.o: %.cxx
	$(CXX) $(CFLAGS) $(INCL) -c $< -o $@

#-----------------------------------------------------------------------------
clean:
	\rm -rf $(OBJS) $(DEPS) tbMainOsci.cxx SyscVpiTimeStub.cxx FabricServer
	\rm -rf work modelsim.ini *.transcript *.log dpi.o dpi.so *.wlf run.do *dpiheader.h
	\rm -f dconn-501* *.vstf RemoteSyscClient RemoteRawcClient
	\rm -f *.cmp
