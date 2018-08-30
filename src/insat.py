# Example: INSAT custom formatting utility routines
"""
These functions are meant to allow full flexibility in formatting an INSAT message.

* One must be familiar with the data content of an INSAT transmission.
* Please see insat_test.py for tests and additional illustrations.
"""

from sl3 import *


def even_parity_bits(num, bits):
    """
    Computes even parity on the provided int
    Only said number of bits are computed

    :param num:  number whose parity should be computed
    :param bits: number of relevant bits in num to compute parity on
    :returns: 1 if parity bit should be set to 1, 0 otherwise
    :rtype: int
    """
    tally = 0
    for bit in range(bits):
        if num & (1 << bit):
            tally += 1
    if tally % 2 == 0:
        return 0
    else:
        return 1


def bit_write(msg, position, set):
    """
    Sets or clears the bit in the specified position of the INSAT message

    :param msg: this is the 25 byte (199 bit) bytestring that is the insat message
    :param position: bit position in msg where to encode the value.  time starts at bit 0, C1 at bit 5
    :param set: bool indicating whether to set or clear the bit
    """

    if position > 199:
        raise ValueError('Bit position exceeds 199. Given: {0!r}'.format(position))
    else:
        byte_pos = int(position / 8)
        bit_mask = 0x80 >> (position % 8)
        if set:
            msg[byte_pos] |= bit_mask
        else:
            msg[byte_pos] &= ~bit_mask


def insat_encode_val(msg, val, position, bits, add_parity):
    """
    Encodes the provided value into the INSAT message
    For S1, S2.. S10 and C1, C2, C3, the number of bits should be set to 10, parity enabled

    :param msg: this is the 25 byte (199 bit) bytestring that is the insat message
    :param val: the value to encode (int)
    :param position: bit position in msg where to encode the value.  time starts at bit 0, C1 at bit 5
    :param bits: how many bits of the value to encode
    :param add_parity: a bool indicating whether to add a parity bit
    :returns: position moved forward by bits and parity
    :rtype: int
    """

    for val_pos in range(bits):
        bit_set = 0
        if (val >> (bits - val_pos - 1)) & 1:
            bit_set = 1
        bit_write(msg, position + val_pos, bit_set)
    new_pos = position + bits

    if add_parity:
        parity_set = 0
        if even_parity_bits(val, bits):
            parity_set = 1
        bit_write(msg, position + bits, parity_set)
        new_pos += 1

    return new_pos


def insat_10_bit(val):
    """
    Converts provided sensor or calibration reading into a 10 bit number
    Rounds down the provided value
    If value is out of range, it gets set to 0 or 1023

    :param val: sensor or cal reading 
    :type val: float
    :return: 10 bit integer
    """
    i = int(val)  # convert from float to int
    # limit to 10 bit range
    if i < 0:
        i = 0
    elif i > 1023:
        i = 1023

    return i


def insat_encode_data(time_hours, health, cal, sensor):
    """
    Encodes the whole INSAT message

    :param time_hours: time of transmission in hours, int
    :param health: 10 bits of health info, int
    :param cal: three values for calibration data
    :param sensor: 10 sensor values, S1 through S10
    :return: encoded INSAT msg as a bytearray
    """
    msg = bytearray(25)  # create a bytearray filled with zeroes
    pos = 0  # bit position tracker

    pos = insat_encode_val(msg, time_hours, pos, 5, False)  # time
    pos = insat_encode_val(msg, insat_10_bit(cal[0]), pos, 10, True)  # C1
    pos = insat_encode_val(msg, insat_10_bit(cal[1]), pos, 10, True)  # C2
    pos = insat_encode_val(msg, insat_10_bit(cal[2]), pos, 10, True)  # C3
    pos = insat_encode_val(msg, health, pos, 10, True)  # health
    for i in range(10):
        pos = insat_encode_val(msg, insat_10_bit(sensor[i]), pos, 10, True)  # Sensor
        pos = insat_encode_val(msg, i, pos, 4, False)  # index

    return msg


@TXFORMAT
def insat_a1(standard):
    """custom formatting routine
    shows how to create a fixed insat message"""
    msg = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x00\x11\x12\x13\x14\x15\x16\x17\x18\x19\x20\x21\x22\x23\x24'
    return msg


@TXFORMAT
def insat_a2(standard):
    """custom formatting routine
    shows how to create a new message"""
    msg = bytearray(25)  # create a bytearray filled with zeroes
    msg[0] = 0x30
    msg[1] = 0x31
    msg[10] = 0xFE
    msg[18] = 0xB9
    # continue to set all 25 bytes (199 bits of which are valid)

    return msg


@TXFORMAT
def insat_a2_two_msg(standard):
    """This custom formatting routine prepares two different messages
    The first 25 bytes (bytes 0 to 24) have the first message
    The second 25 bytes (bytes 25 to 49) are for the second message
    INSAT TDMA sends two transmissions.  If there are two different messages,
    each is sent.  If not, the same message is repeated twice."""

    # create a 50 byte bytearray filled with zeroes
    msg = bytearray(50)

    # fill the first message with data
    for i in range(25):
        msg[i] = i;

    # fill the second message with data
    for i in range(25, 50):
        msg[i] = 0x80 + i - 25;

    return msg



@TXFORMAT
def insat_a3(standard):
    """This custom formatting routine illustrates how to
    create a complete custom INSAT message"""

    # get the current time in hours
    hours = utime.localtime(time_scheduled())[3]

    # put the calibration values into a list
    cal = [None] * 3
    cal[0] = batt() * 10  # convert to a number that can fit into a 10 bit value
    cal[1] = internal_temp() + 100  # another conversion
    cal[2] = 0

    # set the 10 bit health value
    health = 0b1000000000
    # set bit 9 if the clock has been updated since last transmission
    if is_clock_updated():
        health = health | 0b0100000000

    # put the sensor readings into a list
    # have S1 correspond to measurement M1, S2 to M2, etc
    sensor = [None] * 10
    for i in range(10):
        sensor[i] = measure(i + 1, READING_LAST).value  # sensor values go 0 to 9, measurements go from 1 to 10

    # call the encoder that will create the insat message
    msg = insat_encode_data(hours, health, cal, sensor)
    return msg


