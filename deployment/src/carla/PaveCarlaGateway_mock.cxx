//----------------------------------------------------------------------------//
// Unpublished work. Copyright 2021 Siemens                                   //
//                                                                            //
// This material contains trade secrets or otherwise confidential             //
// information owned by Siemens Industry Software Inc. or its affiliates      //
// (collectively, "SISW"), or its licensors. Access to and use of this        //
// information is strictly limited as set forth in the Customer's applicable  //
// agreements with SISW.                                                      //
//----------------------------------------------------------------------------//

//extern "C" {

#include <Python.h>

#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <netdb.h>

#include <pthread.h>

#include "EmuTlmApiPthreaded.h"

#include "ConvertVpiSimTime.h"

#include "VsiEthGateway.h"
#include "VsiVideoToFabricGateway.h"

//#define DEBUG

using namespace EmuTlmApi;
using namespace XlEtherPacketSnooper;

static VsiEthGateway *ethGateway = NULL;
static VsiVideoToFabricGateway *videoGateway = NULL;
static EmuTlmApiPthreaded *dSession = NULL;

enum { QUANTUM_RATIO = 1 };

const unsigned SOURCE_PORT_ID = 0;
const unsigned  DESTINATION_PORT_ID = 1;

static unsigned char macAddresses[][ETH_ADDR_NUM_BYTES] = {
    { 0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc},   // Port 0 - CARLA client2
    { 0x33, 0x33, 0x00, 0x00, 0x00, 0x16} }; // Port 1 - ROS control client1

static unsigned char ipAddresses[][IPV4_ADDR_NUM_BYTES] = {
    { 192, 168, 1, 10 },   // Port 0 - CARLA client2
    { 192, 168, 1, 11 } }; // Port 1 - ROS control client1

// Set the RTOS timeout for .1 seconds, expressed in NS, and adjusted by
// the ~QUANTUM_RATIO~ we're using in this simulation.
const unsigned long long RTOS_TIMEOUT_IN_NS
    = .1 * /*ns-per-sec=*/1e9 / QUANTUM_RATIO;

static bool gotRxEthernetPacket = false;
static unsigned char *rxPayload = NULL;
static unsigned rxPayloadNumBytes = 0;

static unsigned videoSequenceNum = 0;
static unsigned lidarSequenceNum = 0;

void errorOnTransport( const char *functionName,
    int line, const char *file )
{   char messageBuffer[1024];
    sprintf( messageBuffer,
        "%s: Error on transport socket [line #%d of '%s'].\n",
        functionName, line, file );
    SC_REPORT_FATAL( "ETH-FATAL", messageBuffer ); }

//----------------------------------------------------------------------------
// Topic: Forward transport for RX frames wrapper function
//
// This interrupt handler function is registered directly with the
// interrupt target channel (see below). It, in turn, downcasts the ~context~
// to its owning *class FrontBackTester* object, then calls its
// *::nbTransportFw()* method to do the actual handling of the interrupt.
//----------------------------------------------------------------------------

// (begin inline source)
static void rxFrameHandler(
    unsigned char *payload, unsigned numBytes, void */*context*/ ) 
{
    gotRxEthernetPacket = true;
    rxPayload = payload;
    rxPayloadNumBytes = numBytes;
}
// (end inline source)

int initializeConnection(const char* serverUrl, unsigned int domain, unsigned int portNum)
{
    // First establish connection remote TLM fabric server ...
    dSession = new EmuTlmApiPthreaded( serverUrl, domain, portNum,
        "remoteSession" , ":timeServerConduit0", ":resetServerConduit0" );

    ethGateway = new VsiEthGateway( dSession,
        /*txConduitId=*/ ":txEtherFrameConduit10",
        /*rxConduitId=*/ ":rxEtherFrameConduit10",
        /*myMacAddress=*/   macAddresses[SOURCE_PORT_ID],
        /*myIpAddress=*/    ipAddresses[SOURCE_PORT_ID]);

    ethGateway->registerRxCallback( NULL, rxFrameHandler );

    videoGateway = new VsiVideoToFabricGateway( dSession,
        ":videoStream0", /*imageWidth=*/1280, /*imageHeight=*/720 );

    cout << "+=+ INFO: ... successfully connected to TLM FabricServer !" << endl;
    return 0;
}

static PyObject* advanceSimulation(PyObject* self, PyObject* args)
{
    int advanceSuccessful = 1;
    try {
        dSession->advanceNs( RTOS_TIMEOUT_IN_NS );
    }
    catch (...) {
        // Added the catch clause in case the server has exited.
        // This way we can ensure clean exit from the CARLA side.
        advanceSuccessful = 0;
    }

    return Py_BuildValue("i", advanceSuccessful);
}

static PyObject* waitForReset(PyObject* self, PyObject* args) {
    int resetSuccessful = 1;
    try { dSession->waitForReset(); }
    catch (...) {
        // Added the catch clause in case the server has exited.
        // This way we can ensure clean exit from the CARLA side.
        resetSuccessful = 0;
    }

    videoGateway->configure();

    return Py_BuildValue("i", resetSuccessful);
}

// Python Interface APIs: Establish a Connection w/Co-model Host Fabric Server Process
static PyObject* connectToServer(PyObject* self, PyObject* args) {
    char* serverIp;
    char* domainStr;
    int   port;
    unsigned int domain;
    
    if(!PyArg_ParseTuple(args, "ssi", &serverIp, &domainStr, &port))
        return NULL;
    
    if (string(domainStr) == "AF_INET")
        domain = AF_INET;
    else
        domain = AF_UNIX;

    return Py_BuildValue("i", initializeConnection(serverIp, domain, port));
}

// Python Interface APIs: Disconnect from Co-model Host Fabric Server Process
static PyObject* disconnectFromServer(PyObject* self, PyObject* args) {

    // Ship out a special Ethernet frame telling the ROS client to exit
    union {
        uint8_t rawData[16];
        uint64_t uintRep[2];
    } caster;

    caster.uintRep[0] = 0xffffffffffffffff;
    caster.uintRep[1] = 0xffffffffffffffff;

    unsigned char dataPayloadEnd[4] = {0xca, 0xfe, 0xca, 0xfe};

    videoGateway->sendVideoFrame( dataPayloadEnd, 4 );

    ethGateway->sendEthernetPacket( caster.rawData, 2*sizeof(uint64_t),
        macAddresses[DESTINATION_PORT_ID], ipAddresses[DESTINATION_PORT_ID]);

    delete ethGateway;
    delete dSession;

    cout << "Disconnected from TLM FabricServer ..." << endl;;

    return Py_BuildValue("i", 1);
}

// Python Interface APIs: Receive CAN Frame from Co-model Host Fabric Server Process
static PyObject* recvEthernetPacket(PyObject* self, PyObject* args) {
    // Block execution until RX packet received ...
    while( gotRxEthernetPacket == false ) dSession->yield();
    gotRxEthernetPacket = false;
    PyObject *returnedPayload = Py_BuildValue ("y#",
        (const char *)rxPayload, rxPayloadNumBytes );
    return returnedPayload;
}

// Python Interface APIs: Send Ethernet Frame to Fabric Server
static PyObject* sendEthernetPacket(PyObject* self, PyObject* args) {
    unsigned char *dataToSend;
    unsigned char *destMac;
    unsigned char *destIp;
    int dataSize;
    Py_buffer buf;
    Py_buffer bufMac;
    Py_buffer bufIp;
    
    if(!PyArg_ParseTuple(args, "y*y*y*", &buf, &bufMac, &bufIp))
        return NULL;
    
    
    destMac = (unsigned char *) bufMac.buf;
    destIp = (unsigned char *) bufIp.buf;
    
    if (bufMac.len != ETH_ADDR_NUM_BYTES)
    {
        cerr << "Error: Received MAC address with incorrect size: " << bufMac.len << endl;
    }
    if (bufIp.len != IPV4_ADDR_NUM_BYTES)
    {
        cerr << "Error: Received IP address with incorrect size: " << bufIp.len << endl;
    }
    
    dataToSend = (unsigned char *) buf.buf;
    dataSize = buf.len;

    ethGateway->sendEthernetPacket((unsigned char *) dataToSend, dataSize,
        destMac, destIp);

    return Py_BuildValue("i", 1);
}

// Python Interface APIs: Send TLM GP to Fabric Server
static PyObject* sendVideoFrame(PyObject* self, PyObject* args) {
    unsigned char *dataPayload;
    unsigned dataNumBytes;
    Py_buffer buf;
    
    if(!PyArg_ParseTuple(args, "y*", &buf))
        return NULL;

    dataPayload = (unsigned char *) buf.buf;
    dataNumBytes = buf.len;

    // Here we embed a "secret" sequence number byte in the video frame
    // payload. This is useful for tracking dropped frames as they travel
    // through the system. -- johnS 12-19-21
    dataPayload[0] = videoSequenceNum++;

    // And encode a frame type in byte [1]. Type 'v' is a video frame, type 'l'
    // is a lidar frame. -- johnS 5-12-22
    dataPayload[1] = 'v';

    videoGateway->sendVideoFrame( dataPayload, dataNumBytes );

#ifdef DEBUG
unsigned lastIndex = dataNumBytes - sizeof(uint32_t);

printf( "@%lld ns DEBUG sendVideoFrame() numBytes=%d seq#=%d image: "
"[%x %x %x %x] [%x %x %x %x] ... [%x %x %x %x]\n",
convert.timeInNs(), dataNumBytes, dataPayload[0],
dataPayload[0], dataPayload[1], dataPayload[2], dataPayload[3],
dataPayload[4], dataPayload[5], dataPayload[6], dataPayload[7],
dataPayload[lastIndex], dataPayload[lastIndex+1],
dataPayload[lastIndex+2], dataPayload[lastIndex+3] );
#endif

    return Py_BuildValue("i", 1);
}

// -------------------------
// LiDAR frame format
//
// LiDAR header packet is followed by LiDAR point cloud image itself for a
// particular sample in time.
//
// LiDAR header:
// byte 0: seq#
// byte 1: 'l' - denote's LiDAR as opposed to 'v' for video
// byte 2: unused
// byte 3: unused
// byte 4-7: Point cloud array numBytes
// bytes 8-31: LiDAR sensor transform (TF) arranged as array of 6 floats,
//   float x
//   float y
//   float z
//   float pitch
//   float yaw
//   float row
//
// LiDAR point cloud image: array of floats of [x,y,z,i] 4-tuples
// float 0: X
// float 1: Y
// float 2: Z
// float 3: I
// ...

//--------------------------------------------
// sendLidarFrame()

static PyObject* sendLidarFrame(PyObject* self, PyObject* args) {
    unsigned char *headerPayload;
    unsigned headerNumBytes;
    unsigned char *dataPayload;
    float *floatPayload;
    unsigned dataNumBytes;
    Py_buffer header;
    Py_buffer pointCloudData;

    if(!PyArg_ParseTuple(args, "y*y*", &header,&pointCloudData))
        return NULL;

    headerPayload = (unsigned char *) header.buf;
    headerNumBytes = header.len;
    dataPayload = (unsigned char *) pointCloudData.buf;
    dataNumBytes = pointCloudData.len;

    // Here we embed a "secret" sequence number byte in the video frame
    // payload. This is useful for tracking dropped frames as they travel
    // through the system. -- johnS 12-19-21
    headerPayload[0] = lidarSequenceNum++;

    // And encode a frame type in byte [1]. Type 'v' is a video frame, type 'l'
    // is a lidar frame. -- johnS 5-12-22

    headerPayload[1] = 'l';
    *((uint32_t *)&headerPayload[4]) = pointCloudData.len;

    videoGateway->sendVideoFrame( headerPayload, headerNumBytes );

#ifdef DEBUG
floatPayload = (float *)(headerPayload+sizeof(float));

printf( "@%lld ns DEBUG sendLidarFrame() numBytes=%d seq#=%d frameType=%c transform: "
"[x=%f y=%f z=%f] [pitch=%f yaw=%f roll=%f]\n",
convert.timeInNs(), headerNumBytes, headerPayload[0], headerPayload[1],
floatPayload[0], floatPayload[1], floatPayload[2],
floatPayload[3], floatPayload[4], floatPayload[5] );
#endif

    unsigned numFloats = dataNumBytes/sizeof(float);
    floatPayload = (float *)dataPayload;
    for( unsigned i=0; i<numFloats; i+=4 )
        floatPayload[i] = -floatPayload[i];

    videoGateway->sendVideoFrame( dataPayload, dataNumBytes );

#ifdef DEBUG
printf( "@%lld ns DEBUG sendLidarFrame() numBytes=%d numFloats=%d numPoints=%d points: "
"[%f %f %f %f] [%f %f %f %f] [%f %f %f %f]\n",
convert.timeInNs(), dataNumBytes, dataNumBytes/4, dataNumBytes/16,
floatPayload[0], floatPayload[1], floatPayload[2], floatPayload[3],
floatPayload[4], floatPayload[5], floatPayload[6], floatPayload[7],
floatPayload[8], floatPayload[9], floatPayload[10], floatPayload[11] );
#endif

    return Py_BuildValue("i", 1);
}

//--------------------------------------------
// getSimulationTimeInNs()

// Python Interface APIs: Get TLM fabric server simulation time in ns
static PyObject* getSimulationTimeInNs(PyObject* self, PyObject* args) {
    return Py_BuildValue("K", convert.timeInNs());
}

//  Module's Function Definition struct
static PyMethodDef clientMethods[] = {
    { "connectToServer", connectToServer, METH_VARARGS, "Connect to TLM fabric server" },
    { "disconnectFromServer", disconnectFromServer, METH_VARARGS, "Disconnect from TLM fabric server" },
    { "recvEthernetPacket", recvEthernetPacket, METH_VARARGS, "Receive Ethernet frames from TLM fabric server" },
    { "sendEthernetPacket", sendEthernetPacket, METH_VARARGS, "Send Ethernet frames to TLM fabric server" },
    { "sendVideoFrame", sendVideoFrame, METH_VARARGS, "Send video frame to TLM fabric server" },
    { "advanceSimulation", advanceSimulation, METH_VARARGS, "Sync with fabric server RtosInterrupt" },
    { "waitForReset", waitForReset, METH_VARARGS, "Sync with fabric server reset" },
    { "getSimulationTimeInNs", getSimulationTimeInNs, METH_VARARGS, "Get TLM fabric server simulation time" },
    { "sendLidarFrame", sendLidarFrame, METH_VARARGS, "Send LiDAR point cloud image frame to TLM fabric server" },
    { NULL, NULL, 0, NULL }
};

//  Module Definition struct
static struct PyModuleDef PaveCarlaGateway = {
    PyModuleDef_HEAD_INIT,
    "PaveCarlaGateway",
    "C Client Module",
    -1,
    clientMethods
};

// Initializes client module using  above struct
PyMODINIT_FUNC PyInit_PaveCarlaGateway(void) {
    return PyModule_Create(&PaveCarlaGateway);
}

//}
