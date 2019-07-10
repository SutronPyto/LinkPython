
"""
Turn an SDI-12 fan on/off depending on recent sensor data.
"""

import re
import utime
from sl3 import *

status_fan_on = False  # the current status of the fan (true if on)
status_fan_init = False  # did we ever issue a fan control command?

# global radiation results are kept here
# we need to know the maximum reading of the last 20 minutes
# since, we are measuring once a minute, we will store last 20 readings
rad_values = 20  # how many values we store
rad_index = 0  # index into list, points to position we will write next
rad_readings = [0.0] * rad_values  # this is the list of readings


@TASK
def radiation_clear():
    """
    Clears the history of radiation readings.
    """
    global rad_values
    global rad_readings
    global rad_index

    for i in range(rad_values):
        rad_readings[i] = 0.0
    rad_index = 0


def radiation_add_reading(radiation):
    """
    adds a value to the radiation readings history
    overwrites oldest reading with the new one
    """
    global rad_values
    global rad_readings
    global rad_index

    rad_readings[rad_index] = radiation
    rad_index += 1
    if rad_index >= rad_values:
        rad_index = 0


def radiation_max_reading():
    """
    Returns the maximum radiation reading from the list
    """
    global rad_readings
    global rad_index

    maximum = rad_readings[0]
    for i in rad_readings:
        if i > maximum:
            maximum = i

    return maximum


def fan_control(turn_on):
    """
    This function sends an SDI-12 command to a device to control a fan.

    :param turn_on: true to turn fan on, false to turn it off
    :type turn_on: bool
    :return: None
    :rtype:
    """
    global status_fan_on
    global status_fan_init

    # if we are trying to change the status of the fan
    # or if we have never issued a fan control command:
    if (status_fan_on != turn_on) or (not status_fan_init):
        if turn_on:
            command = "0XLn"  # command to turn on fan
        else:
            command = "0XLs"  # command to turn off fan

        sdi_send_command_get_reply(command, "Port1")
        status_fan_on = turn_on
        status_fan_init = True

        # write a log entry for diagnostics
        reading = Reading(label="FanControl", time=utime.time(),
                          etype='E', value=float(turn_on), units="",
                          right_digits=0, quality='G')
        reading.write_log()

    # else - fan is already in correct state - no action required


@TASK
def diagnostics():
    """
    Pints the current fan status and the history of radiation readings
    """
    global status_fan_on
    global rad_values
    global rad_readings
    global rad_index

    print("Fan state: {}, max rad: {}, time: {}".format(
        status_fan_on, radiation_max_reading(), ascii_time(utime.localtime())))

    # the code below prints the history which is a bit much for normal diagnostics
    """
    print("Rad history (not in order): ")
    print(*rad_readings, sep=", ")
    print("\n")
    """


@MEASUREMENT
def radiation_for_fan(radiation):
    """
    This script should be connected to the global radiation measurement.
    Routine will turn the fan on or off based on recent measurements.

    It will keep a history of recent radation measurements.
    It will also access the most recent wind speed average measurement.
    Routine will turn fan on
        If the maximum value of the global radiation of the last 20 minutes is greater than 400
        AND the wind speed average is less than 2.1
    Otherwise, it will turn fan off

    :param radiation: current global radiation reading
    :return: radiation (untouched)
    """

    # should we turn the fan on or off?
    fan_should = False  # assume it should be off

    # add the new reading to the list
    radiation_add_reading(radiation)

    # what is the max radiation from the list?
    maximum = radiation_max_reading()

    # what is the threshold? stored in GP1
    radiation_threshold = float(setup_read("GP1 Value"))

    # check against the limit
    if maximum > radiation_threshold:
        # radiation is high enough.  let's check wind

        # get current wind reading and read the limit from GP setup
        wind_now = measure("WAVG").value
        wind_limit = float(setup_read("GP2 Value"))

        if wind_now < wind_limit:  # we only turn on the fan if there is no wind
            fan_should = True  # we need to turn on the fan

    # take care of the fan
    fan_control(fan_should)

    # print diagnostics if desired
    diagnostics()

    # we must return the untouched radiation reading
    # because it gets logged and transmitted
    return radiation


class Sdi12Error(Exception):
    pass


def sdi_bus_valid(sdi_bus):
    """
    Routine checks whether the provided parameter is a SDI-12 bus

    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: True if provided parameter is a valid bus
    :rtype: Boolean
    """
    bus_upper = sdi_bus.upper()
    if ("PORT1" in bus_upper) or ("PORT2" in bus_upper) or ("RS485" in bus_upper):
        return True
    else:
        return False


def sdi_send_command_get_reply(cmd_to_send, sdi_bus="Port1"):
    """
    Sends provided command out on the specified SDI-12 bus, gets reply from the sensor.

    :param cmd_to_send: the command to send on the SDI-12 bus, e.g. "0M!"
    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: sensor reply, or "No reply"
    :rtype: str
    """

    if sdi_bus_valid(sdi_bus):
        reply = command_line('!SDI {} {}'.format(sdi_bus, cmd_to_send), 128)
        if "Got reply: " in reply:
            reply = reply.replace("Got reply:", "")
    else:
        raise Sdi12Error("No such bus", sdi_bus)

    reply = reply.strip()
    return reply


def sdi_collect(address, command="M", sdi_bus="Port1"):
    """
    Collects data from an SDI-12 sensor using the provided cmd_to_sensor
     It is expected that the sensor will use the same reply format as to aM! cmd_to_sensor

    :param address: int address of SDI-12 sensor to collect data from
    :param command: command to issue to sensor, e.g. "M"
    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: a list of floats containing all the returned parameters
    """

    # create the SDI-12 cmd_to_sensor using the provided address
    cmd_to_sensor = '{0}{1}!'.format(address, command)

    # issue the cmd_to_sensor and get the reply
    sensor_reply = sdi_send_command_get_reply(cmd_to_sensor, sdi_bus)

    # parse out the returned values
    parsed = re.match('(\d)(\d\d\d)(\d)', sensor_reply)
    if parsed is None or int(parsed.group(1)) != address:
        raise Sdi12Error('No reply or bad reply', sensor_reply)

    # figure out how long and then wait for sensor to be ready
    time_till_reply = int(parsed.group(2))
    utime.sleep(time_till_reply)

    # how many parameters did the sensor return?
    values_returned = int(parsed.group(3))

    # all the parameters returned by the sensor end up here
    result = []

    # we will use this expression to parse the values form the sensor reply
    float_match = re.compile('([-+][0-9]*\.?[0-9]+[eE][-+]?[0-9]+)|([-+][0-9]*\.?[0-9]*)')

    # we need to issue one or more send data commands to the sensor
    data_index = 0
    while len(result) < values_returned and data_index <= 9:
        # create and issue the get data cmd_to_sensor
        cmd_to_sensor = '{0}D{1}!'.format(address, data_index)
        sensor_reply = sdi_send_command_get_reply(cmd_to_sensor, sdi_bus)

        if (sensor_reply is None) or (sensor_reply == "No reply"):
            raise Sdi12Error('Missing data at pos', len(parsed) + 1)

        # parse out all the values returned by the sensor
        while len(result) < values_returned:
            parsed = float_match.search(sensor_reply)
            if parsed is None:
                break
            result.append(float(parsed.group(0)))
            sensor_reply = sensor_reply.replace(parsed.group(0), '', 1)

        data_index += 1
    return result


# keep track of the result of the last SDI-12 command
last_custom_result = None

# keep track of the time we issued the last SDI-12 command
last_custom_time = 0


def sdi_collect_improved(address, desired_parameter, command="M", sdi_bus="Port1"):
    """
    Collects data from SDI address 0 using the provided command and returns the
     specified parameter. This version is optimized to not re-issue the command
     each time a different parameter is retrieved, if the data had already been
     retrieved in the past 10 seconds.

    :param address: int address of SDI-12 sensor
    :param desired_parameter: which SDI-12 parameter to return, 0 based
                             (i.e. first param is 0)
    :param command: command to issue, e.g. "M"
    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: the value of the desired SDI-12 parameter
    """

    global last_custom_result
    global last_custom_time
    # if it's been more than 10 seconds since we've collected
    # then collect data now:
    if (utime.time() - last_custom_time) > 10:
        try:
            # perform the custom measurement command
            last_custom_result = sdi_collect(address, command, sdi_bus)
        except Sdi12Error as e:
            last_custom_result = e
        last_custom_time = utime.time()
    # if the last request caused an exception, we will just re-raise that
    # exception:
    if type(last_custom_result) is Sdi12Error:
        raise last_custom_result
    # otherwise return the last value for the requested parameter
    return last_custom_result[desired_parameter]
