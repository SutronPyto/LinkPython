# Example:  Rain during the last 24 hours, Rate of change measurements

from sl3 import *


@MEASUREMENT
def precip_last_24_hours(inval):
    """
    Computes rainfall during the last 24 hours.
        If called at 5PM today, it tells you how much rain fell since 5PM yesterday.
        If called at 8:15AM today, gives rain since 8:15AM yesterday.

    * Reads the current precip accumulation.
    * Reads the precip accumulation from 24 hours ago.
    * Computes result based on difference.

    Must have a measurement setup to log precip accumulation on same schedule
    as this measurement.  It must have a specific label (see below).
    Here is the required setup (interval may be adjusted)::

    !M2 Active=On
    !M2 Label=RAIN ACCU
    !M2 Meas Type=Precip Accumulation
    !M2 Accumulation Reset=Off
    !M2 Meas Interval=00:15:00
    !M3 Active=On
    !M3 Label=RAIN 24h
    !M3 Meas Type=Manual Entry
    !M3 Meas Interval=00:15:00
    !M3 Use Script=On
    !M3 Script Function=precip_last_24_hours


    :param inval: this value is ignored
    :return: precip during last 24 hours
    :rtype: float
    """

    # the precip accumulation measurement must have this label:
    precip_accu_label = "RAIN ACCU"

    # what index is the precip accumulation measurement?
    precip_accu_index = meas_as_index(precip_accu_label)

    # current reading of precip accumulation
    precip_current = measure(precip_accu_index)

    # compute previous time based on precip reading's timestamp
    # routine is made for 24 hours, but any interval could be used
    time_24_hours_ago = precip_current.time - 24 * 60 * 60

    # Read the log, starting with the newest precip reading
    # and going backwards until we find the oldest reading within the time bounds.
    # That allows us to produce a result before the first 24 hours pass.
    oldest_reading = Reading(value=0.0)
    try:
        logthing = Log(oldest=time_24_hours_ago,
                       newest=precip_current.time,
                       match=precip_accu_label,
                       pos=LOG_NEWEST)

        for itero in logthing:
            oldest_reading = itero

    except LogAccessError:
        print('No logged readings found.  Normal until recording starts.')
        return 0.0

    rain_24_hour = precip_current.value - oldest_reading.value

    if rain_24_hour < 0.0:
        # If the difference is negative, precip accumulation has been reset.
        # Use the current precip accumulation value as the 24 hour value
        rain_24_hour = precip_current.value

    return rain_24_hour


def differential_reading(meas_label, period_sec, allow_negative):
    """
    Computes the difference between the most recent reading of the specified measurement,
    and an older reading of the same measurement.
    Routine reads the log looking for the older reading.

    This is a generic version of the precip_last_24_hours routine.

    :param meas_label: the label of the measurement in question
    :type meas_label: str
    :param period_sec: how long ago the old reading was made in seconds
    :type period_sec: int
    :param allow_negative: should a negative difference be allowed?  set to False for rain accumulation
    :type allow_negative: bool
    :return: the difference between the two readings
    :rtype: float
    """

    # current reading
    current = measure(meas_as_index(meas_label))

    # compute previous time based on current reading and period_sec
    time_old = current.time - period_sec

    # Read the log, looking for the measurement starting with the newest
    # and going backwards until we find the oldest reading within the time bounds.
    oldest_reading = Reading(value=0.0)
    try:
        logthing = Log(oldest=time_old,
                       newest=current.time,
                       match=meas_label,
                       pos=LOG_NEWEST)

        for itero in logthing:
            oldest_reading = itero

    except LogAccessError:
        print('No logged readings found.  Normal until recording starts.')
        return 0.0

    # if both readings are valid, compute the difference
    if (current.quality == 'G') and (oldest_reading.quality == 'G'):
        result = current.value - oldest_reading.value

        if (result < 0.0) and (not allow_negative):
            # If the difference is negative, the measurement has been reset.
            print('Negative change not allowed')
            return current.value
        else:
            print('Change computed successfully')
            return result

    else:
        print('Readings were not valid')
        return 0.0



@MEASUREMENT
def precip_last_hour(inval):
    """
    Computes the precipitation during the last hour.
        Please see  precip_last_24_hours.
        This example uses differential_reading.
        Another measurement labeled RAIN ACCU must be recording precip accumulation.
    """
    return differential_reading("RAIN ACCU", 3600, False) # 3600 sec = 1 hour.  False means no negative readings.


def rate_of_change_2meas_setup(meas_index_or_label):
    """
    Computes the change between the current and the previous readings.
        This script needs to reference another measurement which logs sensor readings.

    Please note that it takes two measurements to compute rate of change.
        The first measurement needs to log the sensor values.
        The second measurement will compute the difference of two sensor values.
    """

    # find the index of the measurement
    meas_index = meas_as_index(meas_index_or_label)

    # find out this measurement's interval
    interval_text = setup_read("M{} Meas Interval".format(meas_index))
    interval_sec = sl3_hms_to_seconds(interval_text)

    meas_label = meas_find_label(meas_index)

    # Find the difference in two readings.  True means allow negative change.
    change = differential_reading(meas_label, interval_sec, True)
    return change


@MEASUREMENT
def roc_m1(inval):
    """
    Computes rate of change for measurement M1.
    This script must be associated with a measurement other than M1.
    """
    return rate_of_change_2meas_setup(1)


""" The variables below are used to compute the rate of change"""
roc_valid = False
roc_previous = 0.0


@MEASUREMENT
def rate_of_change_1meas_setup(inval):
    """
    Computes rate of change for the measurement setup with this script.
    This never logs the value of the sensor.  Instead, it remembers the sensor
    reading and uses it the next time it computes the rate of change.
    """
    global roc_valid
    global roc_previous

    # If we have the previous reading, compute the rate of change.
    # If not, return zero.
    if roc_valid:
        result = inval - roc_previous
    else:
        result = 0.0
        roc_valid = True

    # Remember the current value.  It gets used next measurement cycle.
    roc_previous = inval

    return result


def measurement_previous():
    """
    Gets the previous measurement from the log using the measurement schedule
    Must be called by an @MEASUREMENT function

    Make sure to check the quality of the returned reading!

    :return: previously logged measurement
    :rtype: Reading
    """

    # find the previous reading of this measurement in the log
    time_previous = time_scheduled() - 1  # anything older than current reading
    meas_label = meas_find_label(index())

    # find out this measurement's interval to compute time of previous
    interval_text = setup_read("M{} Meas Interval".format(index()))
    interval_sec = sl3_hms_to_seconds(interval_text)

    try:
        previous_reading = Log(
            oldest=time_previous - interval_sec,
            newest=time_previous,
            match=meas_label).get_newest()

        print("got one from log")
        return previous_reading

    except LogAccessError:
        # could not find it.  create a bad reading
        print("did not find one")
        return Reading(time=time_previous, label=meas_label, value=-999.0, quality="B")
