//----------------------------------------------------------------------------//
// Unpublished work. Copyright 2022 Siemens                                   //
//                                                                            //
// This material contains trade secrets or otherwise confidential             //
// information owned by Siemens Industry Software Inc. or its affiliates      //
// (collectively, "SISW"), or its licensors. Access to and use of this        //
// information is strictly limited as set forth in the Customer's applicable  //
// agreements with SISW.                                                      //
//----------------------------------------------------------------------------//

#include <link.h>
#include <systemc.h>
#include "svdpi.h"

#include "uvmc.h"
#include "XlRemoteTlmConduitPkg.h"

#include "ConvertVpiSimTime.h"

#include "XlSyscTlmResetServer.h"
#include "XlSyscTlmTimeServer.h"

#include <arpa/inet.h>

#include "XlTlmEthSoftSw.h"
#include "XlEthSnooper.h"

using namespace uvmc;

// This function is useful for setting breakpoints on in gdb prior to
// elaboration or anything else happening.
extern "C" { extern char *acc_product_version(void); };

const char    *DEFAULT_SERVER_URL        = "localhost";
const unsigned DEFAULT_DOMAIN            = AF_UNIX;
const unsigned DEFAULT_PORT_NUM          = 50101;

//---------------------------------------------------------
// readArgs()                              johnS 10-12-2012
//---------------------------------------------------------

static int readArgs(
    int argc, char *argv[],
    string &serverUrl,
    unsigned &domain,
    unsigned &portNum )
{   int i, usage = 0;

    char argName[BUFSIZ];
    char argVal[BUFSIZ];

    for( i=1; i<argc && usage == 0; i++ ){

        int numArgs = sscanf( argv[i], "--%[^=]=%s", argName, argVal );

        if( numArgs != 2 ) usage = 1;

        string arg = argName;

        if( arg == "server-url" ) serverUrl = argVal;
        else if( arg == "domain" ) {
            arg = argVal;
            sscanf( argVal, " %d", &domain );

            if(      arg == "AF_INET" ) domain = AF_INET;
            else if( arg == "AF_UNIX" ) domain = AF_UNIX;
            else usage = 1;
        }
        else if( arg == "port-num" )   sscanf( argVal, " %d", &portNum );
        else usage = 1;
    }

    if( usage ) {
        printf( "usage: FabricServer\n" );
        printf( "    --server-url=<server IP addr> (default: localhost) |\n" );
        printf( "    --domain=AF_INET | AF_UNIX    (default: AF_INET)   |\n" );
        printf( "    --port-num=<value>            (default: 50101)\n" );
    }
    return( usage );
}

//____________________                                     ___________________
// class FabricServer \___________________________________/hishamab 17-11-2020
//----------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Title: class FabricServer: Top level SC_MODULE on TLM fabric server side
// ---------------------------------------------------------------------------
//
// The top level ~FabricServer~ instantiates an Ethernet TLM software switch 
// (*class XlTlmEthSoftSw*) with two TLM Ethernet ports for connection with the
// two remote clients.
//
// See the full system diagram in the section 
// <demoCarlaRosGatewayUntethered/ Overview> and accompanying description for 
// more information about the ~system-of-systems~ topology.
// 
// In addition to the components mentioned above to implement the full
// functionality of the system of communicating Ethernet models, there are a 
// couple of additional components for routine housekeeping such as sync'ing 
// on system reset and advancing time
//
// | XlSyscTlmResetServer  # Open-kit TLM reset server
// | XlSyscTlmTimeServer   # Open-kit TLM time server
//----------------------------------------------------------------------------

class FabricServer : public sc_module {

  private:

    enum { NUM_CLIENTS = 2 };

    XlSyscTlmResetServer *resetServer;
    XlSyscTlmTimeServer *timeServers[NUM_CLIENTS];
    
    XlTlmEthSoftSw *softSwitch;
    XlEthSnooper *snooper;
    
    SC_HAS_PROCESS(FabricServer);

  public:
    //---------------------------------------------------------
    // Constructor/destructor
    //---------------------------------------------------------

    FabricServer( sc_module_name name ) : sc_module(name) {

        softSwitch = new XlTlmEthSoftSw( "softSwitch", /*numPorts=*/2 );
        snooper = new XlEthSnooper( "snooper" );

        fprintf( stdout,
            "\n\n+=+ INFO: ::FabricServer(): ModelSim Version: %s\n\n",
            acc_product_version() );

        sc_core::sc_report_handler::set_actions(
            sc_core::SC_FATAL, sc_core::SC_THROW | sc_core::SC_DISPLAY );

        // Create reset server and time servers for the remote clients.
        // The reset interval was chosen to match the tethered version.
        resetServer = new XlSyscTlmResetServer(
            "resetServer", /*numTargetSockets=*/NUM_CLIENTS,
            /*resetIntervalInNs=*/60 );
        timeServers[0] = new XlSyscTlmTimeServer( "timeServer0" );
        timeServers[1] = new XlSyscTlmTimeServer( "timeServer1" );

        //------------------------------------------------
        // Topic: Stitch it all together with UVM-Connect
        //
        // Here we ~UVM-Connect~ all the various TLM-2.0 ports of the components
        // mentioned above so as to stitch together the entire TLM fabric
        // portion of the system that is running on this local server process.
        //
        // Notice also that, while not required, here we use ~class
        // uvmc_xl_converter~ as the ~packer/unpacker~. This has shown to be
        // substantially faster than the native packer/unpackers that come with
        // the UVM-Connect package because it uses exclusively pass-by-reference
        // semantics for the data and byte enable payloads. Also unlike the
        // default packers/unpackers, this one has no limitation on data
        // payload sizes. See detailed comments in
        //
        // | $UVMC_HOME/src/connect/s*
        // |   uvmc_xl_converter_pkg.sv
        // |   uvmc_xl_converter.h
        //
        // for more info.

        // (begin inline source)

        // UVM-Connect the untethered ResetServer and TimeServer ports
        resetServer->connect( 0, ":resetServerConduit0" );
        resetServer->connect( 1, ":resetServerConduit1" );

        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            timeServers[0]->advanceTargetSocket, ":timeServerConduit0" );
        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            timeServers[1]->advanceTargetSocket, ":timeServerConduit1" );

        // Connect the TX direction ...
        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            *softSwitch->txPorts[0], ":rxEtherFrameConduit10" );
        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            *softSwitch->txPorts[1], ":rxEtherFrameConduit01" );
        // Connect the RX direction ...
        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            *softSwitch->rxPorts[0], ":txEtherFrameConduit10" );
        uvmc_connect < uvmc_xl_converter<tlm_generic_payload> > (
            *softSwitch->rxPorts[1], ":txEtherFrameConduit01" );

        // Can uncomment this for less verbosity and hence better performance.
        //softSwitch->enableMonitoring(false);
        softSwitch->analysisPort.bind( *snooper );

        // (end inline source)
    }

    ~FabricServer(){
        delete softSwitch;
        
        delete resetServer;
        for( unsigned i=0; i<NUM_CLIENTS; i++ ) delete timeServers[i];
    }

    void start_of_simulation(){
        // Parse command line args
        int argc = sc_argc();
        const char * const *argv = sc_argv();
        
        string serverUrl = DEFAULT_SERVER_URL;
        unsigned domain  = DEFAULT_DOMAIN;
        unsigned portNum = DEFAULT_PORT_NUM;

        if( readArgs( argc, (char **)argv, serverUrl, domain, portNum ) )
            return;
        
        // Establish connection to both remote clients.
        XlRemoteTlmConduit::connectToClient( "remoteSession", domain, 50101 );
        XlRemoteTlmConduit::connectToClient( "remoteSession2", domain, 50102 );
        XlRemoteTlmConduit::listenForAllClients();
        fprintf( stdout, "+=+ INFO: FabricServer::start_of_simulation() "
            "Waiting for client connections ...\n" );
        fflush( stdout );
    }
};
