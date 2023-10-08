//----------------------------------------------------------------------------//
// Unpublished work. Copyright 2021 Siemens                                   //
//                                                                            //
// This material contains trade secrets or otherwise confidential             //
// information owned by Siemens Industry Software Inc. or its affiliates      //
// (collectively, "SISW"), or its licensors. Access to and use of this        //
// information is strictly limited as set forth in the Customer's applicable  //
// agreements with SISW.                                                      //
//----------------------------------------------------------------------------//

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <vector>
#include <string>

using namespace std;

#include "systemc.h"

extern void tbMain( int argc, char *argv[] );

//---------------------------------------------------------
// This is a implementation function acc_product_version for use with
// TBX. It is created so that code that calls acc_product_version()
// (which is useful for specifying initial breakpoints in gdb), will
// work in either native MTI mode (where acc_product_version() is natively
// defined), or TBX.
//===========================================================================

extern "C" {

char *acc_product_version(void){ return (char *)"OSCI-SystemC-XL"; }

} /* extern "C" */

//---------------------------------------------------------
// sc_main()                                 johnS 1-5-2004
//
// This is the SystemC "main()" from which all else happens.
//---------------------------------------------------------

int sc_main( int argc, char *argv[] ){

    try {
        tbMain( argc, argv );

        // Kick off SystemC kernel ...
        sc_start();
    }
    catch( string message ) {
        cerr << message << endl;
        cerr << "Fatal Error: Program aborting." << endl;
        return -1;
    }
    catch(sc_report message) {
        cout << "Error: SystemC report:" << endl;
        cout << "Type: "        << message.get_msg_type() << endl;
        cout << "Message: "     << message.get_msg() << endl;
        cout << "Severity: "    << message.get_severity() << endl;
        cout << "Where: line #" << message.get_line_number()
             << " in "          << message.get_file_name() << endl;
        cout << "Fatal Error: Program aborting." << endl;
        return -1;
    }
    catch(sc_exception message) {
        cerr << "Error: SystemC exception:" << endl;
        cerr << message.what() << endl;
        cerr << "Fatal Error: Program aborting." << endl;
        return -1;
    }
    catch(...) {
        cerr << "Error: Unclassified exception." << endl;
        cerr << "Fatal Error: Program aborting." << endl;
        return -1;
    }

    return 0;
}

#define SC_MODULE_EXPORT( tb ) \
    void tbMain( int argc, char *argv[] ){ \
        tb *myTestbench = new tb( "myTestbench" ); \
        static void *gccnowarn = &gccnowarn + (long)myTestbench; \
    }
