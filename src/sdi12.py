# Example:  Module provides SDI-12 examples

"""
The basis for SDI-12 communication is the command line command SDI,
which may be used to issue any data on any SDI-12 bus on Satlink
"""

import re
import utime
from sl3 import *


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
