"""module tests out routines from insat.py"""
from insat import *


def test_insat_parity():
    assert (even_parity_bits(0b001, 3) == 1)
    assert (even_parity_bits(0b011, 3) == 0)
    assert (even_parity_bits(0b100, 3) == 1)
    assert (even_parity_bits(0b101, 3) == 0)
    assert (even_parity_bits(0b111, 3) == 1)
    assert (even_parity_bits(0b1011, 3) == 0)
    assert (even_parity_bits(0b1011, 4) == 1)
    assert (even_parity_bits(0b0000000011, 10) == 0)
    assert (even_parity_bits(0b1111111111, 2) == 0)
    assert (even_parity_bits(0b1000000000, 10) == 1)
    assert (even_parity_bits(0b1100000000, 10) == 0)
    assert (even_parity_bits(0b0111111111, 10) == 1)
    assert (even_parity_bits(0b1111111111, 10) == 0)

    assert (even_parity_bits(0b000, 3) == 0)


def test_insat_bit_write():
    """tests the bit_write function"""
    msg = bytearray(25)  # create a bytearray filled with zeroes

    bit_write(msg, 0, 1)
    assert (msg[0] == 0x80)
    bit_write(msg, 0, 0)
    assert (msg[0] == 0x00)

    bit_write(msg, 7, 1)
    assert (msg[0] == 0x01)
    bit_write(msg, 6, 1)
    assert (msg[0] == 0b00000011)

    bit_write(msg, 8, 1)
    assert (msg[1] == 0x80)
    bit_write(msg, 15, 1)
    assert (msg[1] == 0b10000001)

    msg = bytearray(25)
    pos = insat_encode_val(msg, 0b01100, 0, 5, False)
    assert (pos == 5)
    assert (msg[0] == 0x60)


def test_insat_data_buffer_empty(debug_out):
    """tests out the fixed data buffer empty message
    it shows how to encode all the fields one by one
    it offers the option of outputting bit position information (set debug_out to true)
    """
    msg = bytearray(25)  # create a bytearray filled with zeroes
    pos = 0

    if debug_out: print("Bit position {:03d} Time".format(pos))
    pos = insat_encode_val(msg, 0b01100, pos, 5, False)  # time

    if debug_out: print("Bit position {:03d} C1".format(pos))
    pos = insat_encode_val(msg, 0b0000000000, pos, 10, True)  # C1

    if debug_out: print("Bit position {:03d} C2".format(pos))
    pos = insat_encode_val(msg, 0b0111111111, pos, 10, True)  # C2

    if debug_out: print("Bit position {:03d} C3".format(pos))
    pos = insat_encode_val(msg, 0b1111111111, pos, 10, True)  # C3

    if debug_out: print("Bit position {:03d} Health".format(pos))
    pos = insat_encode_val(msg, 0b1100000000, pos, 10, True)  # health

    if debug_out: print("Bit position {:03d} S1".format(pos))
    pos = insat_encode_val(msg, 0b0000000001, pos, 10, True)  # S1
    pos = insat_encode_val(msg, 1, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S2".format(pos))
    pos = insat_encode_val(msg, 0b0000000010, pos, 10, True)  # S2
    pos = insat_encode_val(msg, 2, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S3".format(pos))
    pos = insat_encode_val(msg, 0b0000000100, pos, 10, True)  # S3
    pos = insat_encode_val(msg, 3, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S4".format(pos))
    pos = insat_encode_val(msg, 0b0000001000, pos, 10, True)  # S4
    pos = insat_encode_val(msg, 4, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S5".format(pos))
    pos = insat_encode_val(msg, 0b0000010000, pos, 10, True)  # S5
    pos = insat_encode_val(msg, 5, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S6".format(pos))
    pos = insat_encode_val(msg, 0b0000100000, pos, 10, True)  # S6
    pos = insat_encode_val(msg, 6, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S7".format(pos))
    pos = insat_encode_val(msg, 0b0001000000, pos, 10, True)  # S7
    pos = insat_encode_val(msg, 7, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S8".format(pos))
    pos = insat_encode_val(msg, 0b0010000000, pos, 10, True)  # S8
    pos = insat_encode_val(msg, 8, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S9".format(pos))
    pos = insat_encode_val(msg, 0b0100000000, pos, 10, True)  # S9
    pos = insat_encode_val(msg, 9, pos, 4, False)  # index

    if debug_out: print("Bit position {:03d} S10".format(pos))
    pos = insat_encode_val(msg, 0b1000000000, pos, 10, True)  # S10
    pos = insat_encode_val(msg, 10, pos, 4, False)  # index

    if debug_out: print(''.join('\\x{:02x}'.format(x) for x in msg))
    assert (msg == b'\x60\x00\x7F\xFF\xFB\x00\x00\x31\x00\xA4\x02\x4C\x08\xA0\x21\x50\x82\xC2\x05\xC8\x0C\x20\x19\x80\x34')
    return msg


def test_insat_msg_a1():
    # this message uses the calibration values hardcoded in Satlink
    # and sensor readings of 0 for S1, 1 for S2, etc
    time = 12
    health = 0b0100000000
    cal = [0, 511, 1023]
    sensor = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected_result = b'\x60\x00\x7F\xFF\xF9\x00\x80\x00\x00\x62\x01\x48\x03\x18\x09\x40\x14\xA0\x31\x80\x7B\x81\x18\x02\x52'

    msg = insat_encode_data(time, health, cal, sensor)
    assert (msg == expected_result)

    return msg


def test_insat_msg_a2():
    # just like  test_insat_msg_a1 but with different sensor values
    # S1 is 1, S2 is 2, etc
    time = 12
    health = 0b0100000000
    cal = [0, 511, 1023]
    sensor = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # slightly different from test_insat_msg_a1
    expected_result = b'\x60\x00\x7F\xFF\xF9\x00\x80\x30\x00\xA2\x01\x88\x04\x98\x0A\x40\x18\xA0\x3D\x80\x8B\x81\x28\x02\x92'

    msg = insat_encode_data(time, health, cal, sensor)
    assert (msg == expected_result)

    return msg


def test_insat_all():
    """ routine calls all the test functions"""
    test_insat_parity()
    test_insat_bit_write()
    test_insat_data_buffer_empty(False)  # set this to true to see bit position info
    test_insat_msg_a1()
    test_insat_msg_a2()

    # insat_a1 routine will return a fixed message.  it does not matter what we pass in
    msg = insat_a1("does not matter")
    assert (msg[0] == 0x00)
    assert (msg[10] == 0x00)
    assert (msg[20] == 0x20)
    assert (msg[24] == 0x24)

    # insat_a2 routine will return a fixed message.  it does not matter what we pass in
    msg = insat_a2("does not matter")
    assert (msg[0] == 0x30)
    assert (msg[1] == 0x31)
    assert (msg[10] == 0xFE)
    assert (msg[18] == 0xB9)

    # just call these functions to ensure no errors
    insat_a2_two_msg("does not matter")
    insat_a3("does not matter")
