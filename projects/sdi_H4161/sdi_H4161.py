"""
script outputs measurement results on SDI-12 bus to an H4161 which converts
them to 4-20mA output

based on K1IntWel.txt basic program for
Kaweah No 1 Intake Gage data conversion to Analog Output

associated with a setup file that has the following measurements setup:
M1 is the H331 Gage Height at the 201 River gage shelter
M2 is the output from the Panametrics AVM for canal flow gage no. 202
M3 is the output from the Panametrics AVM for fish release gage no. 201a
M4 is the output from the H377 that measures the outside air temperature
M5 is the output from the H377 that measures the water temperature
S1 is the script task that runs this script
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


@TASK
def sdi_4_20():
    """
    Converts measurement results to SDI-12 commands for H4161
    """
    #  201 River ght to analog output (0-16 feet)
    f = measure(1).value / 16 * 16 + 4  # yes f/16*16 = f, but consistency

    #  202 AVM canal flow to analog output (0-30 cfs)
    g = measure(2).value / 30 * 16 + 4

    #  201a AVM fish release flow to analog output (0-20 cfs)
    h = measure(3).value / 20 * 16 + 4

    #  Air Temp to analog output (0-130 deg F)
    i = measure(4).value / 130 * 16 + 4

    #  Stilling Well Water Temp to analog output (0-100 deg F)
    j = measure(5).value / 100 * 16 + 4

    """
    use extended command to set analog output values 
    The sdi12 address of the river (201) H4161 is set to "2"
    The sdi12 address of the Canal AVM (202) H4161 is set to "3"
    The sdi12 address of the Fish Release AVM (201a) H4161 is set to "4"
    The sdi12 address of the Air temp H4161 is set to "5"
    The sdi12 address of the Water Tmep H4161 is set to "6"
    
    delays of 100 milliseconds are used to allow adequate time for writing to the SDI12 bus
    """
    right_digits = 1  # as per H4161 manual examples

    cmd = '2XSM{0:.{1}f}!'.format(f, right_digits)
    sdi_send_command_get_reply(cmd)
    utime.sleep(0.1)

    cmd = '3XSM{0:.{1}f}!'.format(g, right_digits)
    sdi_send_command_get_reply(cmd)
    utime.sleep(0.1)

    cmd = '4XSM{0:.{1}f}!'.format(h, right_digits)
    sdi_send_command_get_reply(cmd)
    utime.sleep(0.1)

    cmd = '5XSM{0:.{1}f}!'.format(i, right_digits)
    sdi_send_command_get_reply(cmd)
    utime.sleep(0.1)

    cmd = '6XSM{0:.{1}f}!'.format(j, right_digits)
    sdi_send_command_get_reply(cmd)
    utime.sleep(0.1)
