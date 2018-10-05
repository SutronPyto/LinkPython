"""
    USGS NADP

    This script is meant for a system that uses a Pluvio2 rain gauge along with
    two rain collectors.  The system tracks whether the rain collectors' lids are
    open or closed.

    !!!This script file is associated with a Satlink setup!!!
"""

from sl3 import *
import utime

# Analog lid sensor: if voltage is above this value,
#   lid is considered open
lid_threshold = 0.5

# Digital lid open sensor: if it closes the circuit when
#   the lid is open, set to 1
digital_lid_open = 1

# How often the lid sensor is checked
lid_check_interval_sec = 5

# How often stage is checked
stage_check_interval_sec = 15*60

# how much precipitation is required for wet exposure
intensity_threshold = 0.001

# how many collectors?  you will need to check all the code if you modify this
collectors_in_system = 2

# collector lid: last time we checked, was it open (True) or closed (False)?
lid_is_open = [False, False]

# Tallies of collector states
cycle_tally = [0, 0]  # how many times has the collector closed?
open_tally = [0, 0]  # how many intervals has the collector been open for?

# Results computed from tallies
wet_result = [0.0, 0.0]
dry_result = [0.0, 0.0]
mis_result = [0.0, 0.0]
cyc_result = [0, 0]


def collector_reset_tallies(indicator):
    """
    Call to reset collector tallies

    :param indicator: Which collector?  (0 or 1)
    :type indicator: int
    :return: None
    """
    global collectors_in_system
    global lid_is_open
    global cycle_tally
    global open_tally

    if indicator < collectors_in_system:
        cycle_tally[indicator] = 0
        open_tally[indicator] = 0
        #  lid_is_open[indicator] = False  # do not zero out collector state!


@TASK
def collector_reset_everything():
    """
    Call to reset collector tallies
    If you want to be able to reset the collector tallies without rebooting the system.
    Tie this into a Script Task and run it via LinkComm to reset tallies on command.
    Do not mark the Script Task as Active!
    """

    collector_reset_tallies(0)
    collector_reset_tallies(1)

    global wet_result
    global mis_result
    global dry_result
    global cyc_result
    wet_result = [0.0, 0.0]
    dry_result = [0.0, 0.0]
    mis_result = [0.0, 0.0]
    cyc_result = [0, 0]


def log_lid_event(indicator, is_open):
    """
    Call to write a log entry when the lid opens or closes
    :param indicator: Which collector?  (0 or 1)
    :type indicator: int
    :param is_open: Did the collector just open or just close?
    :type is_open: bool
    :return:
    :rtype:
    """

    # format up the log event label to be Lid1 or Lid2 based on collector
    log_label = "Lid{}".format(indicator+1)  # +1 to go from 0 based to 1 based

    # log value 1 to mean it opened, 0 to mean it closed
    log_value = 0.0
    if is_open:
        log_value = 1.0

    reading = Reading(label=log_label,
                      value=log_value, right_digits=0,
                      time=time_scheduled(),
                      etype='E', quality='G')
    reading.write_log()


def print_status(indicator):
    """ Prints out a status that may be seen via LinkComm's Script Tab"""
    global collectors_in_system
    global lid_is_open
    global cycle_tally
    global open_tally

    status = "Collector {} status @ ".format(indicator+1)
    status += ascii_time(utime.time())
    if lid_is_open[indicator]:
        status += ": Open"
    else:
        status += ": Closed"
    status += ", Cycles: {}".format(cycle_tally[indicator])
    status += ", Exposed: {} sec".format(
        open_tally[indicator] * lid_check_interval_sec)

    print(status)


def collector_check(indicator, is_open):
    """
    Call periodically to tally collector status.

    :param indicator: Which collector?  (0 or 1)
    :type indicator: int
    :param is_open m: Is the collector open right now?
    :type is_open: bool
    :return: None
    """

    if indicator < collectors_in_system:

        if is_open:
            open_tally[indicator] += 1
            if not lid_is_open[indicator]:  # it just opened
                log_lid_event(indicator, True)

        else:
            if lid_is_open[indicator]:  # just closed
                cycle_tally[indicator] += 1
                log_lid_event(indicator, False)

        lid_is_open[indicator] = is_open

        print_status(indicator)


def collector_sensor(indicator, sensor_result):
    """
    Call after reading the collector lid sensor to tally collector status

    :param indicator: Which collector?  (0 or 1)
    :type indicator: int
    :param sensor_result: the collector lid sensor reading
    :type sensor_result: float
    :return: NULL
    """

    # is this an analog or a digital sensor?
    sensor_type = setup_read("M{} Meas Type".format(index()))

    is_open = False  # is the lid open?
    if 'ANALOG' in sensor_type.upper():
        if sensor_result >= lid_threshold: # means the lid is open
            is_open = True

    else:  # digital
        if sensor_result == digital_lid_open:  # means the lid is open
            is_open = True

    collector_check(indicator, is_open)


@MEASUREMENT
def collector_sensor_1(sensor_result):
    """
    This should be called by the measurement that reads the collector
    lid sensor.

    :param sensor_result: the collector lid sensor reading
    :type sensor_result: float
    :return: the same sensor result that was passed to this routine
    """
    collector_sensor(0, sensor_result)
    return float(sensor_result)  # return is meaningless but required by Satlink Python


@MEASUREMENT
def collector_sensor_2(sensor_result):
    """Just like collector_sensor_1, but for the second collector"""
    collector_sensor(1, sensor_result)
    return float(sensor_result)  # return is meaningless but required by Satlink Python


def collector_compute_exposure_times(indicator, precip):
    """
    Call to compute the exposure times based on the tallies

    :param indicator: Which collector?  (0 or 1)
    :type indicator: int
    :param precip: rain accumulation
    :type precip: float
    :return: None
    """

    global intensity_threshold
    global wet_result
    global dry_result
    global mis_result

    if indicator < collectors_in_system:
        # how much time was the lid open for?
        # multiply number of exposed times with the measurement interval
        time_exposed = float(open_tally[indicator]) * float(lid_check_interval_sec)

        if precip > intensity_threshold:  # it rained
            if open_tally[indicator] > 0:  # and the lid was opened
                wet_result[indicator] = time_exposed
                dry_result[indicator] = 0.0
                mis_result[indicator] = 0.0
            else:  # it rained but lid was closed
                wet_result[indicator] = 0.0
                dry_result[indicator] = 0.0
                mis_result[indicator] = stage_check_interval_sec

        else:  # it did not rain
            wet_result[indicator] = 0.0
            dry_result[indicator] = time_exposed
            mis_result[indicator] = 0.0

        # copy cycle count to results
        cyc_result[indicator] = cycle_tally[indicator]

        # we have computed the totals.  reset the tallies.
        collector_reset_tallies(indicator)


@MEASUREMENT
def precip_computation(precip):
    """
    Call when measuring precip so that the exposure results may be computed from the tallies

    :param precip: current rain sensor reading
    :type precip: float
    :return: current rain sensor reading
    :rtype: float
    """
    global collectors_in_system
    for indicator in range(0, collectors_in_system):
        collector_compute_exposure_times(indicator, precip)
    return precip


@MEASUREMENT
def collector_cycles_1(inval):
    """Call to get the number of collector cyc_result"""
    global cyc_result
    return float(cyc_result[0])


@MEASUREMENT
def wet_exposure_1(inval):
    """
    Call to get the wet exposure time
    :param inval: unused
    """
    global wet_result
    return float(wet_result[0])


@MEASUREMENT
def dry_exposure_1(inval):
    """Call to get the dry exposure time"""
    global dry_result
    return float(dry_result[0])


@MEASUREMENT
def missed_exposure_1(inval):
    """Call to get the missed exposure time"""
    global mis_result
    return float(mis_result[0])


@MEASUREMENT
def collector_cycles_2(inval):
    """Call to get the number of collector cyc_result"""
    global cyc_result
    return float(cyc_result[1])


@MEASUREMENT
def wet_exposure_2(inval):
    """Call to get the wet exposure time"""
    global wet_result
    return float(wet_result[1])


@MEASUREMENT
def dry_exposure_2(inval):
    """Call to get the dry exposure time"""
    global dry_result
    return float(dry_result[1])


@MEASUREMENT
def missed_exposure_2(inval):
    """Call to get the missed exposure time"""
    global mis_result
    return float(mis_result[1])


def pseudo_bin_time(time):
    """Converts provided time into pseudobinary YMDHMS"""

    tx_time = utime.localtime(time)

    tx_data = bin6(float(tx_time[0]))  # year
    tx_data += bin6(float(tx_time[1]))  # month
    tx_data += bin6(float(tx_time[2]))  # day
    tx_data += bin6(float(tx_time[3]))  # hour
    tx_data += bin6(float(tx_time[4]))  # min
    tx_data += bin6(float(tx_time[5]))  # sec

    return tx_data.decode('utf-8')  # convert from bytes to string


@TXFORMAT
def pseudo_bin_a1(original_message):
    """ Satlink will  format all the measurements into a
    pseudobinary message.  This routine will touch up that message
    so that it contains the date and time at the start.

    Pseudobinary B formatting has a header that is 2 or 3 bytes
        For random transmissions: 2 byte header
            the first byte is '2' and the second byte is the time offset
        For other transmissions: 3 byte header
            the first byte is 'B', the second is the group number, the third the time offset
    """

    # copy the header from the original message
    if original_message[0] == '2':
        tx_data = (original_message[:2])  # copy 2 bytes
    else:
        tx_data = (original_message[:3])  # copy 3 bytes

    # put time in the message
    tx_time = pseudo_bin_time(time_scheduled())
    tx_data += str(tx_time)

    # copy the original message over, except the header
    if original_message[0] == '2':
        tx_data += original_message[2:]
    else:
        tx_data += original_message[3:]

    return tx_data

