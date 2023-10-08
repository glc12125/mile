from distutils.core import setup, Extension
import os

XL_VIP_HOME = os.getenv('XL_VIP_HOME')
UVMC_HOME = os.getenv('UVMC_HOME')
PAVE360VSI_LIBS = os.getenv('PAVE360VSI_LIBS')
PAVE360VSI_HOME = os.getenv('PAVE360VSI_HOME')

UVMC_LIB_LIBS = UVMC_HOME + '/lib/rawc/client/' + \
    os.getenv('UVMC_BUILD_PLATFORM')
XL_VIP_LIBS = XL_VIP_HOME + '/lib/lib_remote/' + os.getenv('XL_BUILD_PLATFORM')
PAVE360VSI_LIBS_OBJECTS = PAVE360VSI_LIBS + '/' + \
    os.getenv('UVMC_BUILD_PLATFORM') + '/remote/rawc'
print("XL_VIP_HOME: {}".format(XL_VIP_HOME))
print("UVMC_HOME: {}".format(UVMC_HOME))
print("PAVE360VSI_LIBS: {}".format(PAVE360VSI_LIBS))
print("PAVE360VSI_HOME: {}".format(PAVE360VSI_HOME))
print("UVMC_LIB_LIBS: {}".format(UVMC_LIB_LIBS))
print("XL_VIP_LIBS: {}".format(XL_VIP_LIBS))
print("PAVE360VSI_LIBS_OBJECTS: {}".format(PAVE360VSI_LIBS_OBJECTS))

module = Extension('PaveCarlaGateway',
                   include_dirs=[PAVE360VSI_HOME+'/include', XL_VIP_HOME+'/lib', UVMC_HOME+'/src/connect/rawc',
                                 UVMC_HOME+'/src/connect/rawc/tlm_lite', XL_VIP_HOME+'/lib/lib_remote'],
                   libraries=['uvmc_tlm_fabric', 'xl_vip_open_kit',
                              'xl_vip_tlm_xactors', 'xl_vip_open_kit_stubs', 'VsiGateways'],
                   library_dirs=[PAVE360VSI_LIBS_OBJECTS,
                                 XL_VIP_LIBS, UVMC_LIB_LIBS],
                   sources=['PaveCarlaGateway_mock.cxx'])

setup(name='PaveCarlaGateway', version='1.0', ext_modules=[module])
