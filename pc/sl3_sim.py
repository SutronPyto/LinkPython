"""
This module provides a PC simulation of the Satlink API.
The goal of the module is to facilitate the development of Satlink Python code on the PC.
Please note that the functions in here do not necessarily act the same way as their Satlink equivalents do.

"""
import utime


def MEASUREMENT(val):
    """
    Return function that was decorated with MEASUREMENT. 
    This decorator is required for functions used by Satlink Measurements.

    :param function val: function name
    :return: function name
    :rtype: function
    """
    return val


def TASK(val):
    """
    Return function that was decorated with TASK. 
    This decorator is required for functions used by Satlink Script Tasks.

    :param function val: function name
    :return: function name
    :rtype: function
    """
    return val


def TXFORMAT(val):
    """
    Return function that was decorated with FORMATTER.
    This decorator is required for functions used by Satlink to format transmission data.

    :param function val: function name
    :return: function name
    :rtype: function
    """
    return val


class LogAccessError(Exception):
    pass


def log_simtime(n):
    """
    Creates a log time stamp based on current time offset by the number provided.
    For every n, time moves forward by 15 minutes
    """
    today = list(utime.localtime())
    today[4] = 0
    today[5] = 0
    return utime.mktime(today) + n * 60 * 15


class _Log_Simulation:
    """
    This class simulates the SL3 Log
    """
    data = [
        (log_simtime(0), "stage", 5.22, "ft", "G", 2, "M"),
        (log_simtime(0), "temp", 68.4, "deg", "G", 1, "M"),
        (log_simtime(1), "stage", 5.20, "ft", "G", 2, "M"),
        (log_simtime(1), "temp", 67.4, "deg", "G", 1, "M"),
        (log_simtime(2), "stage", 4.72, "ft", "G", 2, "M"),
        (log_simtime(2), "temp", 66.8, "deg", "G", 1, "M")
    ]
    pos = len(data)
    dir = None


def get_newest_entry():
    """ returns the most recent (newest) entry in the log as a tuple """
    _Log_Simulation.dir = -1
    _Log_Simulation.pos = len(_Log_Simulation.data) - 1
    return _Log_Simulation.data[_Log_Simulation.pos]


def get_oldest_entry():
    """ returns the least recent (oldest) entry in the log as a tuple """
    _Log_Simulation.dir = 1
    _Log_Simulation.pos = 0
    return _Log_Simulation.data[_Log_Simulation.pos]


def get_newer_entry():
    """ returns the next (newer) entry in the log as a tuple """
    _Log_Simulation.dir = 1
    if _Log_Simulation.pos >= (len(_Log_Simulation.data) - 1):
        raise LogAccessError("get_newer_entry failed")
    _Log_Simulation.pos += 1
    return _Log_Simulation.data[_Log_Simulation.pos]


def get_older_entry():
    """ returns the previous (older) entry in the log as a tuple """
    _Log_Simulation.dir = -1
    if _Log_Simulation.pos == 0:
        raise LogAccessError("get_older_entry failed")
    _Log_Simulation.pos -= 1
    return _Log_Simulation.data[_Log_Simulation.pos]


def get_entry():
    """ returns the next entry as a tuple based on the last direction accessed """
    if _Log_Simulation.dir is None:
        result = get_newest_entry()
        _Log_Simulation.dir = 1
        return result
    elif _Log_Simulation.dir > 0:
        return get_newer_entry()
    else:
        return get_older_entry()


def write_log_entry(entry):
    """ writes the provided entry (a touple) to the log """
    _Log_Simulation.data.append(entry)


# used to track simulated battery voltage
_batt_volt = 12.5


def internal_sensor(which_sensor):
    """
    Measures one of Satlink's internal sensors
    
    :param which_sensor: integer indicating which sensor to measure
        0: battery voltage
        1: internal temperature, C
        2: Satlink amplifier temperature, C
    :return: sensor reading
    :rtype: float
    """
    if which_sensor == 0:
        from random import randint
        global _batt_volt
        _batt_volt = max(min(_batt_volt + (randint(0, 200) - 100) / 1000.0, 14.9), 8.5)
        return _batt_volt
    elif which_sensor == 1:
        return 21.0
    else:
        return 23.0


def more_info():
    """
    Returns a tuple with additional information, including meas index, 
    whether the measurement was scheduled, time of scheduled measurement, 
    and whether Python is under test.

    :return: 
        The first value [0]:
            The first value is the index and it works for measurements, tx format, and for scripts.  
            If a script from measurement M2 uses the script, the index will be 2.
            For SL3 environmental satellite transmissions only, this value is true if the clock
            has been updated since the last transmission

        The second value [1]:
            The second value indicates whether a measurement or script task was scheduled.  
            If True, measurement/script happened on a schedule while recording was on.  
            If False, measurement/script was initiated by an event such as user interaction.  
            For tx format, the value indicates whether the transmission is of the scheduled kind, 
            as opposed to random or alarm.

        The third value [2]:
            The third value is the scheduled time of the measurement/script task/transmission.

        The fourth value [3]:
            The fourth value is a boolean indicating whether Python is being tested.  
            If a Python function is being tested by the customer, the value is True.  If the function was invoked by Satlink as a part of normal operation, the value is False.

        The fifth value [4]:
            This value is reserved

        The sixth value [5]:
            For SL3 environmental satellite transmissions only, this value is true if the clock
            has been updated since the last transmission

    :rtype: tuple
    """
    return [1, False, utime.mktime(utime.localtime()), True, 4, True]


def return_info(action):
    """
    Function allows script to affect various Satlink actions.
    No immediate action is taken when this script is called.
    It is only once the script has finished executing that the returned info is considered.
    Do not call directly, instead look to wrapper functions in sl3.py

    :param action:
        which satlink action to affect:
            0 - cause MEASUREMENT to NOT log reading
            1 - cause MEASUREMENT to log log reading value
    :type action: int
    :return: None
    """
    return None


class Tls:
    pass


def c_tls():
    """ 
    This is the PC side simulation of thread local storage 
    Please see sl3.tls for details
    """
    return Tls


def c_measure(meas_index, meas_action):
    """
    This functions provides the last or a live reading of a measurement.
    This is the PC simulation version.
    :return: a tuple that may be used to create a Reading object 
    """

    # time, label, value, units, quality, right_digits,
    # type ('M' measurement, 'E' event, 'D' debug)
    return (utime.time(),  # time
            "Sensor",  # label
            15.5,  # value
            "C",  # units
            "G",  # quality
            2,  # right digits
            "M")  # type ('M' measurement, 'E' event, 'D' debug)


def c_command_line(command, buf_size=512):
    """
    This is the PC side simulation of Satlink's command line.

    :param str command: command line function to execute, e.g. "Hello"  "!M1 LAST"
    :param int buf_size: size of buffer for reply
    :return: command line reply
    :rtype: str
    """
    import re
    from random import randint, uniform

    com_upper = command.upper()

    for meas in ("MEAS", "LAST"):
        if meas in com_upper:
            if "CSV" not in com_upper:
                loc_time = utime.localtime(utime.time())
                str_time = "{:02d}:{:02d}:{:02d}".format(00, int(loc_time[4] / 10) * 10, int(loc_time[5] / 5) * 5)
                return "M{} Temp, {:.4f}, 2017/05/05 {}, \r\n".format(re.search(r"\d+", com_upper).group(0),
                                                                      uniform(21.15, 27.89), str_time, )
            else:
                loc_time = utime.localtime(utime.time())
                str_time = "{:02d}:{:02d}:{:02d}".format(00, int(loc_time[4] / 10) * 10, int(loc_time[5] / 5) * 5)
                return "2017/05/05,{},Temp,{:.4f},,G\r\n".format(str_time, uniform(21.15, 27.89))

    for meas in ("TIME", "INTERVAL"):
        if meas in com_upper:
            loc_time = utime.localtime(utime.time())
            return "{:02d}:{:02d}:{:02d}\r\n".format(00, int(loc_time[4] / 10) * 10, int(loc_time[5] / 5) * 5)

    if "M9 SLOPE" in com_upper:
        if "=TEST" in com_upper:
            return "Setup Not changed\r\n"
        elif "=1.23" in com_upper:
            return ""
        elif "=4.56" in com_upper:
            return ""
        elif "=789" in com_upper:
            return ""
        else:
            return "1.0"

    for meas in ("DIGITS", "SLOPE", "OFFSET", "NUMBER"):
        if meas in com_upper:
            return "{}\r\n".format(randint(2, 5))

    if "VER" in com_upper:
        return "\
Sutron Satlink 3 Logger V2 Version 8.22 Build  10:10:10 11/11/2018 revision 2920\r\n\
PIC     7.11\r\n\
GPS     u-blox 1.00 (59842), 00070000\r\n\
WiFi    1.00\r\n\
SL3 S/N 19XY892, Micro 0, Tx 0\r\n\
Radios Installed: Environmental Satellite\r\n"

    if "STATION NAME" in com_upper:
        if "=" in com_upper:
            return ""
        return "Sutron Satlink 3\r\n"

    if "UNITS" in com_upper:
        return "°C\r\n"

    if "MISSING" in com_upper:
        return "Measurement M1 Temp No Reading\r\n"

    if "SERIALNO" in com_upper:
        if "PRODUCT" in com_upper:
            return "1511012"
        if "MICRO" in com_upper:
            return "1511023"
        else:
            return "1511034"

    if "SDI" in com_upper:
        # Sutron SDR 'simulator'
        # expects SDR is at address 0
        if ("0M!" in com_upper) or ("0X!" in com_upper):
            # this sensor returns 7 values immediately
            return "Got reply: 00007\r\n"
        if "0D0!" in com_upper:
            # these are the values returned
            return "Got reply: 0+1.1111-2.222+3.33\r\n"
        if "0D1!" in com_upper:
            # these are the values returned
            return "Got reply: 0+4.4+5-2.5e-45+43.56E+4\r\n"
        if "I!" in com_upper:
            return "Got reply: 013 SUTRON SDR001V3.36\r\n"
        # match 0! last as it is a substring of previous cases!
        if "0!" in com_upper:
            return "Got reply: 0\r\n"
        else:
            return "No reply\r\n"

    if "M1 LABEL" in com_upper:
        return "RH"

    if "M2 LABEL" in com_upper:
        return "AT"

    if "M3 LABEL" in com_upper:
        return "DP"

    if "M4 LABEL" in com_upper:
        return "stage"

    if "ALARM 1 THRESHOLD" in com_upper:
        return "15.0"

    # general purpose variable testing expects these values
    if "GP1 LABEL" in com_upper:
        if "=" in com_upper:
            return ""
        return "Threshold 1"
    if "GP2 LABEL" in com_upper:
        return "Threshold 2"
    if "GP3 LABEL" in com_upper:
        return "Threshold 3"
    if "GP4 LABEL" in com_upper:
        return "Threshold 4"
    if "GP5 LABEL" in com_upper:
        return "Threshold 5"
    if "GP6 LABEL" in com_upper:
        return "Threshold 6"
    if "GP7 LABEL" in com_upper:
        return "Threshold 7"
    if "GP8 LABEL" in com_upper:
        return "Threshold 8"
    if "GP9 LABEL" in com_upper:
        return "Threshold Reset"
    if "GP10 LABEL" in com_upper:
        return "Rapid Up"
    if "GP11 LABEL" in com_upper:
        return "Rapid Down"
    if "GP12 LABEL" in com_upper:
        return "Rain 24h"
    if "GP13 LABEL" in com_upper:
        return "Rain 2h"
    if "GP14 LABEL" in com_upper:
        return "Stage Limit"
    if "GP1 VALUE" in com_upper:
        if "=" in com_upper:
            return ""
        return "1.0"
    if "GP2 VALUE" in com_upper:
        return "2.0"
    if "GP3 VALUE" in com_upper:
        return "3.0"
    if "GP4 VALUE" in com_upper:
        return "4.0"
    if "GP5 VALUE" in com_upper:
        return "5.0"
    if "GP6 VALUE" in com_upper:
        return "4.6"
    if "GP7 VALUE" in com_upper:
        return "3.7"
    if "GP8 VALUE" in com_upper:
        return "2.2"
    if "GP9 VALUE" in com_upper:
        return "0.5"
    if "GP10 VALUE" in com_upper:
        return "2.2"
    if "GP11 VALUE" in com_upper:
        return "1.1"
    if "GP12 VALUE" in com_upper:
        return "1.0"
    if "GP13 VALUE" in com_upper:
        return "0.2"
    if "GP14 VALUE" in com_upper:
        return "2.5"

    return "hello\r\n"


def _reflect_word(c):
    result = 0
    for i in range(16):
        result = (result << 1) | (c & 1)
        c >>= 1
    return result


def _add_crc16(crc, c, poly):
    crc ^= c << 8
    for i in range(8):
        if crc & 0x8000:
            crc = (crc << 1) ^ poly
        else:
            crc <<= 1
    return crc


def _add_crc16_reflected(crc, c, poly):
    crc ^= c
    for i in range(8):
        if crc & 1:
            crc = (crc >> 1) ^ poly
        else:
            crc >>= 1
    return crc


def c_crc(data, polynomial, initial, reflect, invert, reverse):
    if isinstance(data, str):
        data = bytes(data, "latin1")
    crc = initial
    if reflect:
        reflected_poly = _reflect_word(polynomial)
        for c in data:
            crc = _add_crc16_reflected(crc, c, reflected_poly)
    else:
        poly = polynomial & 0xffff
        for c in data:
            crc = _add_crc16(crc, c, poly)
    if invert:
        crc ^= 0xffff
    if reverse:
        crc = (crc >> 8) | ((crc & 0xff) << 8)
    return crc & 0xffff
