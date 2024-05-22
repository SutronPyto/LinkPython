"""
module provides a means of writing a modbus register over the serial port
to change serial port parameters, modify mod_write_raw
to change modbus details (device ID, register to write, value to write), modify modbus_write
hook modbus_write to a script task, or to a measurement (chagne @TASK to @MEASUREMENT)

"""
from sl3 import *
from serial import *
import struct


def mod_write_raw(data_to_write, bytes_in_reply):
    """
    writes the data provided to the serial port for modbus communication
    :param data_to_write: data to send on the port
    :param bytes_in_reply: how long the reply is expected to be
    :return: reply
    """
    try:
        seri = Serial()  # create port and do not open yet
        seri.port = "RS485"
        seri. baudrate = 19200
        seri.parity = 'E'  # 'E' for even parity
        seri.rs485 = True  # obligatory for using RS485
        seri.timeout = 1  # timeout in seconds

        seri.open()
        seri.write(data_to_write)
        seri.flush()  # wait for all bytes to be sent

        reply = seri.read(bytes_in_reply)

        seri.close()
        return reply

    except:
        return None


def modbus_write_register(device_addy, register, data_to_write_16_bit):
    """
    :param device_addy:
    :param register:
    :param data_to_write_16_bit:
    :return:

    modbus write multiple holding registers message
    bytes function
    1 device address
    1 function is 0x10 (write multiple regisgters)
    2 starting register address (lowest address is 0)
    2 data packing - always packs 2 bytes per register
    1 byte count
    X data
    2 CRC
    """

    message = struct.pack('>b', device_addy)
    message += b'\x10'
    message += struct.pack('>H', register)  # >H means pack big endian
    message += b'\x00' + b'\x01' + b'\x02'
    message += struct.pack('>H', data_to_write_16_bit)
    message += struct.pack('<H', crc_modbus(message))  # the CRC byte order is reversed compare to rest of message

    reply = mod_write_raw(message.decode('utf-8'), 5)  # convert from bytes to string, expect a 5 byte reply
    print("sent: ", message)
    if reply is None:
        print("modbus write failed")
    else:
        print("reply: ", reply)


@TASK
def modbus_write():
    """
    writes hard-coded data to a modbus register
    :return:
    """
    device_id = 1
    register_to_write = 5   # this is a zero based number - the first register is zero
    value_to_write = 1234   # 16 bit number to write

    modbus_write_register(device_id, register_to_write, value_to_write)

