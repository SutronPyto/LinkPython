""" RWS script file
Handles output from an AML sesnor on a serial port.
Three values are expected: ec, temp, uv in this format:
 22.502  20.561  0000.000
Parses and averages the three output values.
Formats result into RWS format <LF>STDDDDSTDDDDSTDDDD<CR>
Outputs formatted data on serial port.

*** A setup is associated with this script.
It is expected that one script task will collect sensor data.
This script will not exit and it will not report status

A second script task will average, format, and output the data.
Measurements may be setup to log the results.

Please note that serial ports are opened as script tasks are run.
Turn off recording to close serial port and end capture.
"""
from sl3 import *
import serial
import re

port = serial.Serial()  # serial port object.  does not open it yet
port_opened = False  # did we open the serial port?
port_quiet = True  # any data on the port recently?

assembled_line = ""  # as we get data from the sensor, we store it here
assembled_drop_it = True  # we drop the first line from the sensor as it may be incomplete

# if there is an error, we set readings to this
error9991 = 9991  # too few or too few good values received
error9999 = 9999  # recorder error

# values parsed from the sensor
parsed_ec = error9999
parsed_temp = error9999
parsed_uv = error9999

""" When we test the script and when we run on the PC, we do not listen for
data from the AML sensor on the serial port.  Instead, we grab data from this
buffer.  The parser throws out the first line as it is most likely incomplete.
There are a few lines of invalid data in there for error handling validation."""
aml_simulated_output = """\
.560  0000.000
 22.502  20.561  0000.000
 22.503  20.566  0000.000
 22.501  20.565  0000.000
 22.507  20.572  0000.000
 22.508  20.572  0000.000
 22.512  20.565  0000.000
 22.514  20.565  0000.000
 22.515  20.567  0000.000
 22.517  20.568  0000.000
 19.112  20.030  0000.000
 19.111  20.031  0000.000
 19.110  20.025  0000.000
19.108  20.026  0000.000
 19.109  20.024  0000.00019.048  19.876  0000.000
 19.050  0000.000
 19.048  19.874  0000.000
 19.045  19.869  0000.000
 19.043  19.863  0000.000
 19.040  19.861  0000.000
 19.042  19.857  0000.000
"""
aml_simulated_index = 0


def port_open():
    # configures and opens the serial port IF port_opened is False
    global port
    global port_opened

    if not port_opened:
        if not is_being_tested():
            port.port = "RS485"
            port.rs485 = True
            port.baudrate = 9600
            port.parity = 'N'
            port.stopbits = 1
            port.rtscts = False
            port.dsrdtr = False
            port.xonxoff = False

            # seconds to wait for first byte.  we expect data every 10 seconds or sooner
            port.timeout = 11
            port.inter_byte_timeout = 0.1  # seconds to wait between bytes
            port.open()
        port_opened = True


def port_close():
    # closes the serial port IF port_opened is True
    global port
    global port_opened

    if port_opened:
        if not is_being_tested():
            port.close()
        port_opened = False


def update_results(ec, temp, uv):
    """
    call once we have a set of samples from the sensor
    copies sensor samples  to global variables
    """
    global parsed_ec, parsed_temp, parsed_uv

    lock()  # thread safe access
    parsed_ec = ec
    parsed_temp = temp
    parsed_uv = uv
    unlock()


""" result_ routines may be plugged into measurements so that Link can log sensor data"""
@MEASUREMENT
def result_ec(ignored_input):
    global parsed_ec

    lock()  # thread safe access
    result = parsed_ec
    unlock()

    return result


@MEASUREMENT
def result_temp(ignored_input):
    global parsed_temp

    lock()  # thread safe access
    result = parsed_temp
    unlock()

    return result


@MEASUREMENT
def result_uv(ignored_input):
    global parsed_uv

    lock()  # thread safe access
    result = parsed_uv
    unlock()

    return result


def simulator_readchar():
    """
    reads the prepared reply from the AML simulator
    returns an int, just like serial.readchar()
    """
    global aml_simulated_index, aml_simulated_output

    result = -1  # -1 means no more data
    if aml_simulated_index < len(aml_simulated_output):
        result = ord(aml_simulated_output[aml_simulated_index])
    aml_simulated_index += 1

    return result


def parse_line(one_line):
    """ Call once we have a whole line of data from the sensor.
    Parases data and computes ec, temp, uv"""

    # We want to verify the data is valid
    valid = True

    if one_line[0] != ' ':
        valid = False
    else:
        # split the string into tokens separated by 2 spaces (skip leading space)
        tokens = one_line[1:].split('  ')

        # this regular expression will match a number at the start of the string
        number_parse = re.compile(r"\d+\.*\d*")

        if len(tokens) != 3:
            valid = False
        else:
            # parse the results
            try:
                ec = float(number_parse.match(tokens[0]).group(0))
                temp = float(number_parse.match(tokens[1]).group(0))
                uv = float(number_parse.match(tokens[2]).group(0))
            except TypeError:
                valid = False

    if not valid:
        ec = error9991
        temp = error9991
        uv = error9991

    update_results(ec, temp, uv)

    # for test builds, print the sensor data as diagnostics
    if is_being_tested():
        print("ec: {:12.4f}, temp: {:12.4f}, uv: {:12.4f}, input: \"{}\"".format(ec, temp, uv, one_line))


def assemble_data(one_byte):
    """
    Assembles incoming serial data into a complete line.
    Once a line is complete, it is parsed for data.

    :param one_byte: byte from serial port
    :type one_byte: int
    :return: True if a line was assembled
    :rtype: bool
    """
    # assembles data incoming on the serial port into lines
    global assembled_line, assembled_drop_it
    line_complete = False

    if one_byte == ord('\r') or one_byte == ord('\n'):
        if assembled_drop_it:
            # Throw out the first line as it is most likely incomplete
            assembled_line = ""
            assembled_drop_it = False
        else:
            if len(assembled_line) < 5:
                # not enough data
                update_results(error9991, error9991, error9991)
                assembled_line = ""
            else:
                # parse the line for data
                parse_line(assembled_line)
                assembled_line = ""
                line_complete = True
    else:
        # add byte to the string
        assembled_line += chr(one_byte)

    return line_complete


@TASK
def capture_aml():
    """
    Captures data from the aml sensor.
    Does not exit until the serial port is closed.
    """

    global port, port_quiet, assembled_drop_it

    # initialize
    update_results(error9999, error9999, error9999)
    assembled_drop_it = True
    being_tested = is_being_tested()  # optimization

    port_open()  # open the port

    keep_looping = True
    while keep_looping:

        # pick up data on the port
        if being_tested:
            one_byte = simulator_readchar()
        else:
            one_byte = port.readchar()

        if one_byte != -1:
            # we got a byte
            port_quiet = False
            assemble_data(one_byte)
        else:
            # if we are testing, end loop when we get all data
            if being_tested:
                keep_looping = False
            else:
                port_quiet = True

        # if recording is stopped, end loop
        if not being_tested:
            if setup_read("Recording").upper() == "OFF":
                keep_looping = False

    port_close()
