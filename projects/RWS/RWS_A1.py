""" RWS script file
Handles output from an AML sesnor on a serial port.
Three values are expected: ec, temp, uv in this format:
 22.502  20.561  0000.000
Parses and averages the three output values.
Formats result into RWS format <LF>STDDDDSTDDDDSTDDDD<CR>
Outputs formatted data on serial port.

*** A setup is associated with this script.
It is expected that one script task will collect sensor data.
This script will keep the RS-485 port open, capture, parse, and keep a sum of the the sensor readings.
This script will not exit while recording is on and it will not report status.

A second script task will process the data.
This script runs periodically, based on the setup interval.
Every time the script runs, it computes the averages based on the sum.
It averages are output on the RS232 port using RWS format.
Script status is updated every time the script runs, showing the sensor data,
number of samples processed, and the formatted output.
The number of samples used depends on the sensor output rate and the interval of the script task.

Measurements may be setup to log the results.
They should run at the same schedule as the script task that does the processing.

Turn off recording to close serial port and end capture.

"""
from sl3 import *
import serial
import re

diagnostics_on = True  # set to True to have system add info to script status

# serial port that the sensor is connected to
port_sensor = serial.Serial()  # serial port object.  does not open it yet
port_opened = False  # did we open the serial port?

assembled_line = ""  # as we get data from the sensor, we store it here
assembled_drop_it = True  # we drop the first line from the sensor as it may be incomplete

sensor_data = ""  # we store some of the last sensor data in here for diagnostics

# if there is an error, we set readings to this
error9991 = 9991  # too few or too few good values received
error9999 = 9999  # recorder error

# sum of values from the sensor
sum_ec = 0.0
sum_tm = 0.0
sum_uv = 0.0
sum_count = 0

# processed sensor data result
proc_ec = error9999
proc_tm = error9999
proc_uv = error9999
proc_valid = False
proc_samples = 0

""" When we test the script and when we run on the PC, we do not listen for
data from the AML sensor on the serial port.  Instead, we grab data from this
buffer.  The parser throws out the first line as it is most likely incomplete.
There are a few lines of invalid data in there for error handling validation."""
aml_simulated_output = """\

.560  0000.000
 22.492  20.561  0000.000
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
 19.048  19.874  0001.000
 19.045  19.869  0001.000
 19.043  19.863  0001.000
 19.040  19.861  0001.000
 19.042  19.857  0001.000
 19.039  19.874  0001.000
 19.038  19.869  0001.000
 19.033  19.863  0001.000
 19.033  19.861  0001.000
 19.030  19.857  0001.000
"""
aml_simulated_index = 0


def sensor_port_open():
    # configures and opens the serial port IF port_opened is False
    global port_sensor
    global port_opened

    if not port_opened:
        if not is_being_tested():
            port_sensor.port = "RS485"
            port_sensor.rs485 = True
            port_sensor.baudrate = 9600
            port_sensor.parity = 'N'
            port_sensor.stopbits = 1

            # seconds to wait for first byte.  we expect data every 10 seconds or sooner
            port_sensor.timeout = 11
            port_sensor.inter_byte_timeout = 0.1  # seconds to wait between bytes
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


def update_results(ec, temp, uv, valid, one_line):
    """
    call once we have a set of samples from the sensor
    copies sensor samples to global variables in a thread safe fashion

    :param ec, temp, uv: sensor values
    :type ec, temp, uv: float
    :param valid: True if values are valid
    :type valid: bool
    :param one_line: one line of sensor data capture on the serial port
    :type one_line: str
    :return: None
    """
    global sum_ec, sum_tm, sum_uv, sum_count, sensor_data

    lock()  # thread safe access

    # keep a sum of the values we have so far
    if valid:
        sum_ec += ec
        sum_tm += temp
        sum_uv += uv
        sum_count += 1

    # remember sensor data (add new line as earlier code strips it)
    if diagnostics_on:
        if len(one_line):
            if len(sensor_data) > 1024*4:  # limit memory usage
                sensor_data = ""
            sensor_data += one_line
            sensor_data += "\n"

    unlock()


def process_results():
    """
    Processes the sensor data we have collected so far
    and updates global variables with results
    """
    global sum_ec, sum_tm, sum_uv, sum_count
    global proc_ec, proc_tm, proc_uv, proc_valid, proc_samples

    lock()  # thread safe access

    if sum_count > 0:
        # if we have enough good samples, compute average
        proc_ec = sum_ec/sum_count
        proc_tm = sum_tm/sum_count
        proc_uv = sum_uv/sum_count
        proc_valid = True
        proc_samples = sum_count
    else:
        # we have no values to process
        proc_ec = error9991
        proc_tm = error9991
        proc_uv = error9991
        proc_valid = False
        proc_samples = 0

    # reset sums
    sum_ec = 0.0
    sum_tm = 0.0
    sum_uv = 0.0
    sum_count = 0

    unlock()


def read_results():
    """ accesses processed sensor data in a thread-safe manner
    by grabbing all results under a single lock, we ensure all results are from the same computation
    :return: ec, temp, uv, valid
    :rtype: float, float, float, bool
    """
    global proc_ec, proc_tm, proc_uv, proc_valid

    lock()  # thread safe access
    r_ec = proc_ec
    r_temp = proc_tm
    r_uv = proc_uv
    r_valid = proc_valid
    unlock()

    return r_ec, r_temp, r_uv, r_valid


@MEASUREMENT
def result_ec(ignored_input):
    """ result_ routines may be plugged into measurements so that Link can log sensor data"""
    ev, temp, uv, valid = read_results()
    return ev


@MEASUREMENT
def result_temp(ignored_input):
    """ result_ routines may be plugged into measurements so that Link can log sensor data"""
    ev, temp, uv, valid = read_results()
    return temp


@MEASUREMENT
def result_uv(ignored_input):
    """ result_ routines may be plugged into measurements so that Link can log sensor data"""
    ev, temp, uv, valid = read_results()
    return uv


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

    update_results(ec, temp, uv, valid, one_line)

    # for test builds, print diagnostics
    if is_being_tested():
        # this is the the last capture and parse from the sensor
        print("ec: {:12.4f}, temp: {:12.4f}, uv: {:12.4f}, input: \"{}\"".format(ec, temp, uv, one_line))

        process_results()  # process it (even though we are averaging just one sample)
        print(format_output())  # format up the output


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
                None  # igonre a single \r or \n (we don't know the exact line terminator)
            elif len(assembled_line) < 5:
                # not enough data
                update_results(error9991, error9991, error9991, False, "")
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
    global port_sensor, assembled_drop_it

    # initialize
    update_results(error9999, error9999, error9999, False, "")
    assembled_drop_it = True
    being_tested = is_being_tested()  # optimization
    sensor_port_open()  # open the port

    keep_looping = True
    while keep_looping:

        # pick up data on the port
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


def format_output():
    """
    Format one line of sensor data into RWS format:
        <LF>STDDDDSTDDDDSTDDDD<CR>
            S= status (space is good, A is bad)
            T= sign (+ or -)
            D= Decimal value (digit)
    e.g.
        <LF> +0289 +0187 +0001<CR>
    :return: formatted data
    :rtype: str
    """
    # get the data we need to format
    ev, tm, uv, valid = read_results()

    # Python does not put a sign in front of a zero.
    # To get +0000, we manually need to do a sign
    ev_s = '+'
    tm_s = '+'
    uv_s = '+'

    # we need to scientifically round all values.
    ev_f = int(ev + 0.5)
    if ev_f < 0.0:
        ev_s = '-'

    if valid:
        tm_f = int(tm*10.0 + 0.5)  # temp needs to be multiplied by 10
    else:
        tm_f = int(tm + 0.5)  # do not multiply by 10 if invalid - it's already 9999
    if tm_f < 0.0:
        tm_s = '-'

    uv_f = int(uv + 0.5)
    if uv_f < 0.0:
        uv_f = '-'

    if valid:
        valid_f = ' '
    else:
        valid_f = 'A'

    result = "\n{0}{1}{2:04d}{0}{3}{4:04d}{0}{5}{6:04d}\r".format(
        valid_f, ev_s, ev_f, tm_s, tm_f, uv_s, uv_f)
    return result


@TASK
def process_and_output():
    """
    Computes the result from the accummulated samples
    Formats the results
    Outputs the format on the serial port
    """
    process_results()
    output_data = format_output()

    with serial.Serial(port="RS232", baudrate=9600, bytesize=8, parity='N',
                       stopbits=1, rtscts=False, dsrdtr=False, xonxoff=False) as output:
        output.write(output_data)
        output.flush()  # needed to make sure all the data is sent before closing the port.

    # diagnostics - these will interfere with performance and should be turned off
    # addtionally, access to sensor_data and proc_samples is NOT properly thread safe
    global diagnostics_on, sensor_data, proc_samples
    if diagnostics_on:
        lock()
        print("formatted output: ", output_data)
        print("samples: ", proc_samples)
        print("sensor data: ")
        print(sensor_data)
        sensor_data = ""  # clear out sensor data
        unlock()


# show debug output when testing on PC
if not sutron_link:
    capture_aml()

