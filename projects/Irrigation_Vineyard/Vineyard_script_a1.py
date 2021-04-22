"""
This script controls an SDI-12 relay in order to irrigate based on soil moisture readings.
There is a setup file associated with this script

A Tekbox TBSRB01 4 channel SDI-12 controlled latching relay is employed.

Soil moisture is checked once when function check_and_irrigate is called - by default, that is once a day at 6AM.
Measurement labeled 'SoilMoist50' by default measures soil moisture.
If soil moisture is below limit (0.30 by default), relays are triggered over an extended time period:
    * Relay 1 is activated and left active for an hour
    * After the hour, relay 1 is deactivated, relay 2 activated, and left active for an hour.
    * Etc. until all four relays have been active for an hour one at a time.
    * The process starts at 6AM and ends at 10AM.

Irrigation is aborted (all relays deactivated) if system is stopped.
When system boots up, relays are all deactivated.
If the script crashes, an attempt is made to deactivate all relays.

Check script status (LinkComm scripts tab) to see updates on script activity.  Unfortunately, the status only updates once the function completes (4 hours).  There is no real time status :(
Whenever a relay is switched, an event is written to the log:
    "Relay, 0" means all relays deactivated
    "Relay, 1" means relay 1 active, all other inactive
    "Relay, 2" means relay 2 active, all other inactive etc.

Check script variables below to change:
    * label of measurement that checks soil moisture
    * soil moisture limit that triggers irrigation
    * how long to irrigate for
    * SDI address of relay
"""

# what is the name of the soil moisture measurement that triggers relays
soil_moisture_meas = "SoilMoist50"

# what is the limit for the soil moisture required to trigger irrigation?
moisture_limit = 0.30

# how long to irrigate for each time in seconds
irrigation_period_sec = 3600 # one hour

# what SDI-12 address is the Tekbox TBSRB01 relay on?
relay_addy = 3

# the SDI-12 bus that the relay is on
relay_bus = "PORT1"

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


def update_status(status):
    """ update the status that we show the user"""
    update = ascii_time(utime.time()) + ' ' + status
    print(update)


def check_reply(reply):
    """
    checks the reply from the relay.  it must say aX_OK
    if it does not, error is logged and False returned
    :param reply: SDI-12 reply from relay
    :type reply: str
    :return: True if no error
    :rtype: bool
    """
    if 'X_OK' in reply:
        return True
    else:
        return False


TIME_UP = 1
STOPPED = 0

def wait_time_or_stop(end_time, sleep_period_sec=5):
    """
    Waits until provided end time or until recording is stopped
    :param end_time: when the wait should end
    :type end_time: u_time.time()
    :param sleep_period_sec: how long to sleep for when checking for recording
    :type sleep_period_sec: int seconds
    :return: TIME_UP (1) or STOPPED (0)
    :rtype: int
    """
    ret_val = TIME_UP

    while(utime.time() < end_time):
        if setup_read("Recording").upper() == "OFF":
            ret_val = STOPPED
            break
        utime.sleep(sleep_period_sec)

    return ret_val


def relay_control(relay_index):
    """
    either opens all relays (relay_index = 0), or
    closes one relay and opens all others (1 <= relay_index <=4)
    updates status with result

    :param relay_index: which relay to close (0 means open all)
    :type relay_index:  int
    :return: True if AOK
    :rtype: bool
    """
    # format up the command:
    # 0 means open relay - stop irrigating
    # 1 means close relay - start irrigating
    if relay_index == 1:
        sdi_cmd = '{}XSR,1,0,0,0'.format(relay_addy)
    elif relay_index == 2:
        sdi_cmd = '{}XSR,0,1,0,0'.format(relay_addy)
    elif relay_index == 3:
        sdi_cmd = '{}XSR,0,0,1,0'.format(relay_addy)
    elif relay_index == 4:
        sdi_cmd = '{}XSR,0,0,0,1'.format(relay_addy)
    else:
        # open all relays
        sdi_cmd = '{}XSR,0,0,0,0'.format(relay_addy)

    reply = sdi_send_command_get_reply(sdi_cmd, relay_bus)
    if check_reply(reply):
        update_status("Relay {} activated".format(relay_index))
        reading = Reading(label="Relay", time=utime.time(),
                          etype='E', value=relay_index, quality='G')
        reading.write_log()
        return True

    else:
        update_status("Relay activation failure, SDI: {}".format(reply))
        reading = Reading(label="Relay", time=utime.time(),
                          etype='E', value=relay_index, quality='B')
        reading.write_log()
        return False


@TASK
def relay_all_deactivate():
    """
    Issues command to open all relays (stops irrigation)
    Connect this to a Script Task
    """
    relay_control(0)


def irrigate():
    """
    Irrigates by controlling  relays over a 5 hour period
    :return: True if irrigation completes, False if aborted
    :rtype: bool
    """
    time_tracker = utime.time()
    result = True

    for relay_index in range(1,5):

        if not relay_control(relay_index):
            result = False  # failed to issue command
            break

        # update time for next end
        time_tracker = time_tracker + irrigation_period_sec

        if not wait_time_or_stop(time_tracker):
            # system was stopped
            update_status("System stopped.  Irrigation aborted.")
            result = False  # failed to issue command
            break

    # deactivate all relays
    relay_all_deactivate()
    return result


@TASK
def check_and_irrigate():
    """
    Routine will check soil moisture and irrigate if appropriate
    Connect this to a Script Task
    """

    try:
        # check soil moisture
        moisture = measure(soil_moisture_meas)
        if moisture.quality != 'G':
            # failed to measure moisture
            update_status("Moisture measurement failed")

        elif moisture.value < moisture_limit:
            # proceed to irrigate
            if is_being_tested():
                # script testing should not irrigate
                update_status("Script test will not irrigate! Soil moisture: {}".format(moisture.value))
            else:
                update_status("Irrigating! Soil moisture: {}".format(moisture.value))
                irrigate() # note that irrigate will update status

        else: # no need to irrigate now
            update_status("No need to irrigate.  Soil moisture: {}".format(moisture.value))

    except:
        # if script breaks, deactivate all relays
        relay_all_deactivate()
