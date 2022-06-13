""" High Sierra IceSight sensor script file
Handles output from an IceSight sesnor on a serial port.

*** A setup is associated with this script.

It is expected that one script task will collect sensor data.
This script will keep the RS-232 port open, capture, and parse the sensor readings.
The script will not exit while recording is on.  Turn off recording to close serial port and end capture.

A second script task may be used to see the last data from the sensor.

Sat/XLink meausrements are connected to certain sensor readings.

sensor output is ASCII and line based (CRLF ending)
values are separated by one or more spaces
we expect 13 or more values, each separated by at least one space
some values are numeric, others descriptive
E.g.
   5000   5000  1.000  25.51  23.75 9 9 MAX MAX 1 1 0.90 0.90 0 GOOD  39.32  26.09  34.14 101

"""
from sl3 import *

import serial
import re

# if the sensor provides no data for this time amount, error!  we expect data every 1 second
sensor_timeout_seconds = 20

# if there is an error, we set readings to this
error9999 = -9999

port_sensor = serial.Serial()  # serial port object.  does not open it yet
port_opened = False  # did we open the serial port?

assembled_line = ""  # as we get data from the sensor, we store it here
assembled_drop_it = True  # we drop the first line from the sensor as it may be incomplete

sensor_line_raw = "No data captured\r\n"  # last line from sensor is stored here
sensor_time_last = 0  # time of last sensor data


def init_data():
    """
    initializes the globals
    :return: None
    """
    global assembled_line, assembled_drop_it, sensor_line_raw, sensor_time_last
    lock()
    assembled_line = ""
    assembled_drop_it = True

    sensor_line_raw = "No data captured\r\n"
    sensor_time_last = 0
    unlock()


""" When we test the script and when we run on the PC, we do not listen for
data from the sensor on the serial port.  Instead, we grab data from this
buffer.  The parser throws out the first line as it is most likely incomplete.
There are a few lines of invalid data in there for error handling validation."""
sensor_simulated_output = """\
 MAX 1 1 0.90 0.90 0 GOOD  39.35  26.09  34.20 101
  5000   5000  1.000  25.51  23.75 9 9 MAX MAX 1 1 0.90 0.90 0 GOOD  39.32  26.09  34.14 101
  5000   5000  1.000  25.47  23.65 9 9 MAX MAX 1 1 0.90 0.90 0 GOOD  39.42  26.09  34.27 101
  5000   5000  1.000  2590 0 GOOD  39.49  26.09  34.45 101
  23.63 9 9 MAX MAX 1 1 0.90 0.90 0 GOOD  39.52  26.09  34.46 101
  5000   5000  1.000  25.51  23.73 9 9 MAX MAX 1 1 0.90 0.90 0 GOOD  39.52  26.09  34.48 101
1321 1210 1.091 32.1 35.4 3 3 WET WET 7 7 0.86 0.86 0 FAIR 32.22 33.55 33.55 -102
1321 1210 1.091 32.1 35.4 3 3 WET WET 7 7 0.86 0.86 0 FAIR 32.22 33.55 33.55 -102
"""
sensor_simulated_index = 0


def sensor_port_open():
    # configures and opens the serial port IF port_opened is False
    # sensor specifies 9600 bps, 8N1, no flow control
    global port_sensor
    global port_opened

    if not port_opened:
        if not is_being_tested():
            port_sensor.port = "RS232"
            port_sensor.baudrate = 9600
            port_sensor.bytesize = 8
            port_sensor.parity = 'N'
            port_sensor.stopbits = 1
            port_sensor.rtscts = False
            port_sensor.dsrdtr = False
            port_sensor.xonxoff = False

            port_sensor.timeout = sensor_timeout_seconds
            port_sensor.inter_byte_timeout = 1  # seconds to wait between bytes
            port_sensor.open()
        port_opened = True


def sensor_port_close():
    # closes the serial port IF port_opened is True
    global port_sensor
    global port_opened

    if port_opened:
        if not is_being_tested():
            port_sensor.close()
        port_opened = False


def read_results(position):
    """ accesses sensor data in a thread-safe manner
    :param position: which sensor parameter to get?  starts at 1!!!
    :return: sensor parameter value or error value
    :rtype: float
    """
    lock()  # thread safe access
    global sensor_line_raw, sensor_time_last
    local_line = sensor_line_raw
    unlock()

    x = local_line.strip(" \t\r\n").split()  # split the line into individual space separated entries

    result = error9999
    if utime.time() - sensor_time_last > sensor_timeout_seconds:
        result = error9999   # data is too old.  sensor could be dead
    elif 1 <= position <= 19:
        index_p = position - 1  # position is one based
        if len(x) >= 13:
            if index_p < len(x):
                try:
                    result = float(x[index_p])
                except ValueError:
                    result = error9999

    return result


def update_status():
    """
    updates the script stats that may be inscpected via the Script tab, Script Status in LinkComm
    returns human readable message
    """

    # thread safe copy of globals
    global sensor_time_last, sensor_line_raw
    lock()
    local_time = sensor_time_last
    local_line = sensor_line_raw
    unlock()

    message = ""
    if not is_being_tested():
        if not port_opened:
            message += "System stopped.  Data not being collected."
    if local_time == 0:
        message += ("No data collected as of {}\n".format(ascii_time(utime.time())))
    else:
        if utime.time() - sensor_time_last > sensor_timeout_seconds:
            message += "TIMEOUT: No recent data from sensor\n"
        message += ("Time last data: {}\n".format(ascii_time(local_time)))
        message += "Data:\n"
        message += local_line
    return message


@TASK
def status():
    print(update_status())


@MEASUREMENT
def surface_temp(x):
    """ x is not relevant """
    result = read_results(5)
    if result == 100.1:  # this is how sensor says error
        return error9999
    else:
        return result


@MEASUREMENT
def displayed_condition(x):
    return read_results(6)


@MEASUREMENT
def measured_condition(x):
    return read_results(7)


@MEASUREMENT
def displayed_friction(x):
    return read_results(12)


@MEASUREMENT
def measured_friction(x):
    return read_results(13)


def simulator_readchar():
    """
    reads the prepared reply from the simulator
    returns an int, just like serial.readchar()
    """
    global sensor_simulated_index, sensor_simulated_output

    result = -1  # -1 means no more data
    if sensor_simulated_index < len(sensor_simulated_output):
        result = ord(sensor_simulated_output[sensor_simulated_index])
    sensor_simulated_index += 1

    return result


def store_line(one_line):
    """ Call once we have a whole line of data from the sensor
    This routine will do a thread safe copy to global storage"""

    lock()  # thread safe access
    global sensor_line_raw, sensor_time_last
    sensor_line_raw = one_line
    sensor_time_last = utime.time()
    unlock()

    # when testing, let's go ahead and print out the line and the values
    if is_being_tested():
        print("line:")
        print(sensor_line_raw)
        print("parsed values")
        for i in range(0, 22):  # go out of bounds intentionally
            print(i, ":", read_results(i))


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
            if len(assembled_line) == 1:
                None  # ignore a single \r or \n
            elif len(assembled_line) < 5:
                # not enough data
                assembled_line = ""
            else:
                # parse the line for data
                store_line(assembled_line)
                assembled_line = ""
                line_complete = True
    else:
        # add byte to the string
        assembled_line += chr(one_byte)

    return line_complete


@TASK
def capture_data():
    """
    Captures data from the sensor.
    Does not exit until the serial port is closed or recording is stopped.
    """
    global port_sensor, assembled_drop_it

    init_data()
    being_tested = is_being_tested()  # optimization
    sensor_port_open()  # open the port

    keep_looping = True
    while keep_looping:

        # pick up data on the port (if testing, pick up from simulator)
        if being_tested:
            one_byte = simulator_readchar()
        else:
            one_byte = port_sensor.readchar()

        if one_byte != -1:
            # we got a byte
            assemble_data(one_byte)
        elif being_tested:
            # no data. if we are testing, end loop when we get all data
            keep_looping = False

        # if recording is stopped, end loop
        if not being_tested:
            if setup_read("Recording").upper() == "OFF":
                keep_looping = False

    sensor_port_close()


if is_being_tested():
    capture_data()
