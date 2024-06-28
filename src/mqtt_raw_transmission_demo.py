# Example:  demonstrates TCP/IP TXMODE by publishing a MQTT message

"""
MQTT RAW TRANSMISSION DEMO USING Python TCPIP TX MODE
=====================================================

This is a limited demo meant to demonstrate that custom protocols can be
implemented with the TCP/IP TXMODE feature. The demo will publish up to
100 bytes of data to a test server. It does not support authentication or
encryption. Certificates could be used to improve on that, but cannot be
shared in a demo like this.

With the following TX1 setup, this script will transmit measurements to the
Mosquitto test MQTT server every hour in CSV format::

!TX1 Enable=On
!TX1 Radio Type=Cell
!TX1 Kind=Scheduled
!TX1 Label=MQTT RAW
!TX1 Scheduled Interval=01:00:00
!TX1 Scheduled Time=00:00:00
!TX1 Data Source=Measurement
!TX1 Format=CSV
!TX1 Custom Script Format=Off
!TX1 Mode=Python TCPIP
!TX1 Secure=Off
!TX1 Use Certificate=Off
!TX1 Mode Function=MQTT_PUBLISH
!TX1 Main Server=test.mosquitto.org
!TX1 Backup Server=
!TX1 Server Port=1883
!TX1 Server Username=
!TX1 Server Password=
!TX1 Server Path=
!TX1 Script Path Command=
!TX1 Script Path Acknowledge=
!TX1 Script Path Configuration=
!TX1 Use Shef Codes=Off
!TX1 Append Batt=Off
!TX1 Append Station Name=Off
!TX1 Append Tx Time=Off
!TX1 Append Serial No=Off
!TX1 Append Tx Count=Off
!TX1 Compress Data=None
!TX1 Skip First Missing=On
!TX1 Retransmit=On
!TX1 Max Tx Time=10 min

One way to view the results is to install Eclipse Mosquitto from https://mosquitto.org/download/ 
and issue the following command from the installation folder::

    mosquitto_sub -h test.mosquitto.org -t test/topic


How this script creates MQTT messages
=====================================

1. **``struct.pack``**:
   - This function is used to convert Python values into a bytes object, following a specified format.
   - Example: ``struct.pack("!H", len(protocol_name))``:
     - ``"!H"`` specifies the format: ``!`` means network byte order (big-endian), and ``H`` means an unsigned short (2 bytes).
     - ``len(protocol_name)`` is the value being packed.

2. **Fixed Header**:
   - The fixed header is the first part of an MQTT control packet, containing the packet type and the remaining length of the packet.

3. **Variable Header**:
   - The variable header includes additional information specific to the packet type. For CONNECT packets, it includes the protocol name, version, connect flags, and keep-alive time.
   
"""

from sl3 import *
import struct

def create_connect_packet(client_id):
    """
    Creates a CONNECT packet to establish a connection to the MQTT server.

    :param client_id: The client ID to use for the connection.
    :type client_id: str
    :return: The constructed CONNECT packet.
    :rtype: bytes
    """
    protocol_name = b"MQTT"
    protocol_level = 0x04  # MQTT version 3.1.1
    connect_flags = 0x02  # Clean session
    keep_alive = 60
    
    # Variable header
    protocol_name_len = struct.pack("!H", len(protocol_name))
    keep_alive = struct.pack("!H", keep_alive)
    variable_header = protocol_name_len + protocol_name + bytes([protocol_level]) + bytes([connect_flags]) + keep_alive
    
    # Payload (Client ID)
    client_id_len = struct.pack("!H", len(client_id))
    payload = client_id_len + client_id.encode('utf-8')
    
    # Fixed header
    remaining_length = len(variable_header) + len(payload)
    fixed_header = struct.pack("!BB", 0x10, remaining_length)
    
    return fixed_header + variable_header + payload

def create_publish_packet(topic, message, message_id):
    """
    Creates a PUBLISH packet to send a message to the MQTT server.

    :param topic: The topic to publish the message to.
    :type topic: str
    :param message: The message to publish.
    :type message: str
    :param message_id: The message identifier for QoS 1.
    :type message_id: int
    :return: The constructed PUBLISH packet.
    :rtype: bytes
    """
    packet_type = 0x30  # PUBLISH
    qos_level = 0x01  # QoS 1
    packet_type_qos = packet_type | (qos_level << 1)
    topic_encoded = topic.encode('utf-8')
    payload = message.encode('utf-8')
    
    # Message Identifier (for QoS 1)
    message_id_bytes = struct.pack("!H", message_id)
    
    remaining_length = 2 + len(topic_encoded) + 2 + len(payload)  # 2 for topic length, 2 for message ID
    fixed_header = struct.pack("!BB", packet_type_qos, remaining_length)
    
    variable_header = struct.pack("!H" + str(len(topic_encoded)) + "s", len(topic_encoded), topic_encoded) + message_id_bytes
    
    return fixed_header + variable_header + payload

def create_disconnect_packet():
    """
    Creates a DISCONNECT packet to close the connection to the MQTT server.

    :return: The constructed DISCONNECT packet.
    :rtype: bytes
    """
    packet_type = 0xE0  # DISCONNECT
    fixed_header = struct.pack("!BB", packet_type, 0x00)
    return fixed_header

def receive_packet(sock, expected_packet_type):
    """
    Receives a packet from the socket and checks if it matches the expected packet type.

    :param sock: The socket object.
    :param expected_packet_type: The expected packet type to receive.
    :type expected_packet_type: int
    :return: The received packet if it matches the expected type, otherwise None.
    :rtype: bytes or None
    """
    sock.settimeout(1.0)
    # Read the fixed header
    packet = sock.recv(2)
    if not packet:
        print("No packet received")
        return None
    packet_type = packet[0] & 0xF0
    remaining_length = packet[1]
     
    if packet_type != expected_packet_type:
        print("Unexpected packet type:", packet_type)
        return None
     
    # Read the remaining packet data
    remaining_packet = sock.recv(remaining_length)
    return packet + remaining_packet

@TXMODE
def MQTT_PUBLISH(sock, message, file_name):
    """
    Main function to handle the MQTT publishing process. It sends CONNECT, PUBLISH, and DISCONNECT packets.

    :param sock: The socket object.
    :param message: The message to publish.
    :type message: str
    :param file_name: Not used in this script but part of the function signature.
    :type file_name: str
    :return: 0 if successful, 1 otherwise.
    :rtype: int
    """
    result = 1  # indicate we failed

    client_id = "testClient"
    topic = "test/topic"
    message_id = 1  # Message identifier for QoS 1

    # make sure the message is 100 bytes or less, this simple demo doesn't support long messages
    message = message[:100]
    
    print("Sending CONNECT packet")
    packet = create_connect_packet(client_id)
    sock.send(packet)
    
    connack_packet = receive_packet(sock, 0x20)
    if connack_packet is None or len(connack_packet) < 4 or connack_packet[3] != 0x00:
        print("Failed to receive a valid CONNACK packet")
        sock.close()
        return result
    
    print("CONNACK packet received successfully")
    
    print("Sending PUBLISH packet")
    packet = create_publish_packet(topic, message, message_id)
    sock.send(packet)
    
    puback_packet = receive_packet(sock, 0x40)
    if puback_packet is None or len(puback_packet) < 4 or puback_packet[2:4] != struct.pack("!H", message_id):
        print("Failed to receive a valid PUBACK packet")
    else:
        # publish worked
        result = 0
    
    print("Sending DISCONNECT packet")
    packet = create_disconnect_packet()
    sock.send(packet)

    return result

# in case version of LinkComm is being used which can't set these fields, we'll set them for it
if setup_read("tx1 label") == "MQTT RAW":
    if setup_read("tx1 mode") != "Python TCPIP":
        setup_write("tx1 mode", "Python TCPIP")
    if setup_read("tx1 mode function") != "MQTT_PUBLISH":
        setup_write("tx1 mode function", "MQTT_PUBLISH")
