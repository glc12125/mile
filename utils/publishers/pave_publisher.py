import os
import struct
from publisher import Publisher
# Import PAVE360 CARLA gateway module
import PaveCarlaGateway as paveCarlaGateway

XL_TLM_SERVER_IP = os.environ.get('XL_TLM_SERVER_IP', default="localhost")
SOCKET_DOMAIN = os.environ.get('SOCKET_DOMAIN', default="AF_UNIX")

PORT_ID_ROS_CONTROL = 1

macAddresses = [[0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc],   # Port 0 - CARLA client
                [0x33, 0x33, 0x00, 0x00, 0x00, 0x16]]  # Port 1 - ROS control client

ipAddresses = [[192, 168, 1, 10],  # Port 0 - CARLA client
               [192, 168, 1, 11]]  # Port 1 - ROS control client


class PavePublisher(Publisher):

    initialised = False

    def __init__(self):
        self.image_counter = 0
        self.vehicle_state_counter = 0
        if not PavePublisher.initialised:
            print("Trying to connect to XL_TLM_SERVER: {}@{}, SOCKET_DOMAIN: {}".format(
                XL_TLM_SERVER_IP, 50101, SOCKET_DOMAIN))
            paveCarlaGateway.connectToServer(
                XL_TLM_SERVER_IP, SOCKET_DOMAIN, 50101)
            print("Successfully connected!")
            # Do an initial time advance to insure that all conduit connections are
            # established from all clients before invoking async operations which
            # could potentially fail if propagated to clients that have not
            # established connections yet (TODO: Make it so TLM fabric
            # infrastructure insures that all conduit connections are established
            # before any TLM traffic commences - just as we do for client+server
            # connections). -- johnS 12-31-20
            resetSuccess = paveCarlaGateway.waitForReset()
            if not resetSuccess:
                raise ConnectionError("Connection to FabricServer broken!")
            print("--- After reset: @",
                  paveCarlaGateway.getSimulationTimeInNs(), " ns")
            PavePublisher.initialised = True

    def publish(self, structured_data):
        print("@", paveCarlaGateway.getSimulationTimeInNs(),
              " ns publish {}th image".format(self.image_counter))
        # Here we broadcast the image frame to the TLM fabric backplane
        # for further processing. This is done over a separate TLM channel
        # that is basically set up as a TLM-2.0 base protocol channel
        # rather than an industry protocol flavored one.
        paveCarlaGateway.sendVideoFrame(structured_data['image'])
        self.image_counter = self.image_counter + 1

        vehicle_state = structured_data['vehicle_state']
        dataToSend = bytearray([vehicle_state['left_blinker'], vehicle_state['right_blinker'], vehicle_state['low_beam'],
                               vehicle_state['high_beam'], vehicle_state['fog_light'], int(vehicle_state['hand_brake']), vehicle_state['reverse']])
        dataToSend.extend(struct.pack("i", vehicle_state['gear']))
        dataToSend.extend(struct.pack("d", vehicle_state['velocity']))
        paveCarlaGateway.sendEthernetPacket(dataToSend,
                                            bytes(
                                                macAddresses[PORT_ID_ROS_CONTROL]),
                                            bytes(ipAddresses[PORT_ID_ROS_CONTROL]))
        self.vehicle_state_counter += 1
        paveCarlaGateway.advanceSimulation()

    def __del__(self):
        # Cannot delete this from here, because this will stop the server
        # paveCarlaGateway.disconnectFromServer()
        pass
