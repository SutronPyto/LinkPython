"""
This script captures data output by the LISST-ABS Acoustic Backscatter Sensor
manufactured by Sequoia Scientific, Inc

This module contains one @MEASUREMENT routine that will
collect data from the sensor

The sensor outputs data on RS232:
9600 with 8 data bits, one stop bit, no parity, and no flow control

By default, the LISST-ABS will automatically start outputting the
computed ACB values out the RS232 connection upon power up.
The values are output at once per second. The values are one
integer per line. The line is terminated with a linefeed character.
We call this the Automatic Mode output.
Please see lisst_simulated_output below for an example.
"""

from sl3 import *
import utime
import serial

""" Is the sensor powered on all the time?
Or Does Satlink manage power to the sensor via SWD#D?"""
powered_all_the_time = True

""" How many samples should be averaged?  One sample/second"""
samples_to_average = 60

""" How long to wait for data from the sensor?"""
sensor_timeout_sec = 30

"""
Below is an example of data output by the sensor.
It is used to test out the code. 
The first few lines are output at power on.
The last few lines are meant to test the code.
"""
lisst_simulated_output = """\
Sequoia Scientific, Inc.
LISST-ABS version 1.42 May 17 2016 14:47:55
Board revision C.
**** Default parameters loaded.
SDI-12 address is 0.
Auto start will begin in 3 seconds. Press <cr> or <Ctrl>C three times to cancel.
+6.03e-02
+6.28e-02
+6.37e-02
+6.43e-02
+6.40e-02
+6.43e-02
+6.43e-02
+6.49e-02
+6.46e-02
+6.46e-02
+6.49e-02
+6.49e-02
+6.43e-02
+6.46e-02
+6.46e-02
+6.49e-02
+6.52e-02
+6.49e-02
+6.49e-02
+6.49e-02
+6.49e-02
+6.49e-02
+6.46e-02
+6.46e-02
+6.49e-02
+6.46e-02
.46e-02
46e-02
6e-02
e-02
-02
02
2
+7777e-02
"""
lisst_simulated_index = 0


def simulator_readchar():
    """
    reads the prepared reply from the simulator
    returns an int, just like serial.readchar()
    """
    global lisst_simulated_index, lisst_simulated_output

    result = -1  # -1 means no more data
    if lisst_simulated_index < len(lisst_simulated_output):
        result = ord(lisst_simulated_output[lisst_simulated_index])
        lisst_simulated_index += 1

    return result


def simulator_readline():
    """
    reads the prepared reply from the simulator
    acts like serial.readline(), returning bytes
    """
    one_line = ""
    while True:
        one_byte = simulator_readchar()
        if one_byte == -1:
            break  # no more data
        else:
            one_line += chr(one_byte)
            if one_byte == ord('\r') or one_byte == ord('\n'):
                break  # we got line terminator
            elif len(one_line) > 512:
                break  # line too long

    return str_to_bytes(one_line)


class CollectResult:
    """
    As we capture data from the sensor, we get one of these results
    """
    TIMEOUT   = -1
    BAD_DATA  = 0
    GOOD_DATA = 1


def collect_one_reading(port):
    """
    Collects one sensor reading on the port

    :param port: Opened serial port to capture data on
    :type port: Serial
    :return: validity , sensor reading
    :rtype: CollectResult, float
    """

    sensor_reading = -999  # assume invalid input
    validity = CollectResult.BAD_DATA

    # pick up data on the port
    if is_being_tested():
        one_line = bytes_to_str(simulator_readline())
    else:
        one_line = bytes_to_str(port.readline())

    if len(one_line) == 0:  # timeout
        validity = CollectResult.TIMEOUT
    else:
        # the output is always in scientific notation e.g "+6.03e-02"
        validity = CollectResult.BAD_DATA
        check = True
        if one_line.count('e') != 1:
            check = False
        elif one_line.count('-') + one_line.count('+') != 2:
            check = False
        elif one_line.count('-') < 1:
            check = False
        elif one_line.count('.') != 1:
            check = False

        if check:
            try:
                sensor_reading = float(one_line)
                validity = CollectResult.GOOD_DATA
            except ValueError:
                None

    return validity, sensor_reading


def collect_sensor_data(port, samples_to_get):
    """
    Captures data from the sensor, collecting specified number of samples and averaging them
    :param port: Opened serial port to capture data on
    :type port: Serial
    :param samples_to_get: number of samples to average
    :type samples_to_get: int
    :return: samples collected, sample average
    :rtype: int, float
    """

    # how many samples did we get
    samples_got = 0

    # the average of the collected samples
    sensor_avg = -999.0

    # we will keep a sum of the samples in here
    sample_sum = 0.0

    # the number of times we failed to get good data
    # this handles the bootup messages
    bad_collections = 0

    while True:
        valid, reading = collect_one_reading(port)

        if valid == CollectResult.GOOD_DATA:
            sample_sum += reading
            samples_got += 1
            if samples_got >= samples_to_get:
                break

        elif valid == CollectResult.BAD_DATA:
            # did not get valid sample.  could be boot up message
            bad_collections += 1
            if bad_collections > 12:  # too many bad lines and we quit
                if not is_being_tested():  # unless we're testing
                    break

        elif valid == CollectResult.TIMEOUT:
            # timeout waiting for data.  quit
            break

    # average the samples
    if samples_got > 0:
        sensor_avg = sample_sum/float(samples_got)

    return samples_got, sensor_avg


@MEASUREMENT
def lisst_meas(ignored):
    """
    Complete measurement of LISST-ABS sensor
    powers sensor on, waits, collects samples, averages, powers sensor off
    :param ignored: this parameter is ignored
    :return: sensor reading
    :rtype: float
    """

    if not powered_all_the_time:
        power_control('SW2', True)
        # wait after powering sensor on
        if not is_being_tested():  # do not wait if we are testing the code
            utime.sleep(45)  # 45 seconds is recommended by the manual

    # open the port
    with serial.Serial("RS232", 9600) as port:
        port.timeout = sensor_timeout_sec  # setup the timeout
        port.flush()  # clear any data waiting in the port

        # collect data
        samples_got, sensor_avg = collect_sensor_data(port, samples_to_average)

    if not powered_all_the_time:
        power_control('SW2', False)

    print("samples", samples_got, "average", sensor_avg)

    if samples_got >= 1:
        return float(sensor_avg)
    else:
        return float(-999.0)


def lisst_test():
    """
    Test routine that uses data from the simulator buffer
    """
    if not sutron_link:  # this is a PC test only
        samples_got, sensor_avg = collect_sensor_data(None, samples_to_average)
        assert(samples_got == 26)
        assert(abs(sensor_avg - 0.06440) < 0.0001)

