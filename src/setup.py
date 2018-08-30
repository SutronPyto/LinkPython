# Example:  provides functions to read and write the setup 

"""This module provides example routines for changing Satlink's setup"""
from sl3 import *


@TASK
def alarm_in_setup_change():
    """script task should be setup when system goes into alarms to increase meas and tx rate"""
    setup_write("!M1 meas interval", "00:01:00")
    setup_write("!M2 meas interval", "00:01:00")
    setup_write("!TX3 scheduled interval", "00:05:00")


@TASK
def alarm_out_setup_change():
    """script task should be setup when system goes out of alarms to slow meas and tx rate"""
    setup_write("!M1 meas interval", "00:10:00")
    setup_write("!M2 meas interval", "00:10:00")
    setup_write("!TX3 scheduled interval", "01:00:00")


def measurement_setup(n):
    """
    function takes the entire setup of a single measurement and places it into a dictionary 
    :param n: measurement index
    :return: dictionary where the setup field name is the key, and the setup field value is the value
    """
    cmd = '!M' + str(n)
    prefix = cmd + ' '
    s = command_line(cmd, 2048).strip()
    return dict((a.replace(prefix, '', 1), b) for a, b in (item.split('=') for item in s.split('\r\n')))


def save_measurement_setup(n, m):
    """
    function saves provided measurement setup to Satlink's permanent storage
    :param n: measurement index
    :param m: a dictionary containing the measurement setup to save; the setup field name is the key, and the setup field value is the value
    :return: success
    """
    prefix = '!M' + str(n) + ' '
    cmd = '\r'.join((prefix + a + '=' + b) for a, b in m.items())
    command_line(cmd, 1)
    return m == measurement_setup(n)


def copy_measurement_setup(n1, n2):
    """
    copies the setup of one measurement to another 
    :param n1: source measurement which will be copied
    :param n2: destination measurement whose setup will be overwritten
    :return: success
    """
    save_measurement_setup(n2, measurement_setup(n1))
