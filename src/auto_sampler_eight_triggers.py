# Example:  Automated sampler program triggers on multiple varied conditions.
"""

Sampler is triggered on multiple, user-settable factors including

* Eight different turbidity triggers
* Rapid changes to stage
* Rainfall

Script also computes rainfall during the last 24 hours
"""

from sl3 import *
import utime

# The sampler has a limited number of bottles.
bottles_capacity = 8

# We count how many bottles are in use.  If losing count on reboot is of concern,
# this could be stored in the general purpose settings.
bottles_used = 0

# Time sampler was triggered last.
time_last_sample = 0.0

# How many seconds need to elapse between two sampler triggers?
min_time_between_samples = 2 * 3600
# Please note that if min_time_between_samples is less than 2 hours,
#   the 2 hour rain threshold may trigger multiple times
#   on the same rainfall.  In that case, a timeout may need to
#   be added to the 2 hour rainfall routine.
#   Same goes for the 24 hour rainfall.


"""
    The following section is a stub for the upcoming addition of general purpose settings.
    There are going to be multiple pairs of settings.  Each one will consist
    of a label (ASCII string) and a value (IEEE32 float).
    The settings will be named
    G1 Label
    G1 Value
    G2 Label
    G2 Value
    ..
    G32 Label
    G32 Value
"""
general_stub = {
    "Threshold 1": 1.0,
    "Threshold 2": 2.0,
    "Threshold 3": 3.0,
    "Threshold 4": 4.0,
    "Threshold 5": 5.0,
    "Threshold 6": 4.6,
    "Threshold 7": 3.7,
    "Threshold 8": 8.0,
    "Rapid Up": 2.2,
    "Rapid Down": 1.1,
    "Rain 24h": 1.0,
    "Rain 2h": 0.2,
    "Stage Limit": 2.5
}
general_entries = len(general_stub)  # how many entries?


def general_read_value(label):
    """Returns the Value associated with the Label of the general purpose setting."""
    return general_stub.get(label)


"""Sampler control section is below."""


def trigger_sampler_master():
    """Triggers the sampler immediately and logs it."""

    global bottles_used
    global time_last_sample

    # increment the number of bottles used
    bottles_used += 1

    # update the time of the last trigger
    time_last_sample = utime.time()

    # trigger sampler by pulsing output for 2 seconds
    power_control('SW2', True)
    utime.sleep(2.0)
    power_control('SW2', False)

    # write a log entry
    reading = Reading(label="Triggered", time=time_scheduled(),
                      etype='E', value=bottles_used,
                      right_digits=0, quality='G')
    reading.write_log()


def trigger_sampler():
    """
    Call to attempt to trigger the sampler.
    Certain conditions may prevent the triggering.

    :return: True if sampler was triggered.
    """
    global bottles_capacity
    global bottles_used
    global time_last_sample
    global min_time_between_samples

    trigger = True

    if bottles_used >= bottles_capacity:
        trigger = False  # out of bottles
    elif (utime.time() - time_last_sample) < min_time_between_samples:
        trigger = False  # too soon since last trigger
    elif is_being_tested():
        trigger = False  # script is being tested
    elif setup_read("Recording").upper() == "OFF":
        trigger = False  # if recording is off, do not sample

    if trigger:
        trigger_sampler_master()  # Call routine that controls sampler.
        return True

    else:
        return False  # Sampler was NOT triggered.


"""The precipitation section is below"""


def differential_reading(meas_label, period_sec, allow_negative):
    """
    Computes the difference between the most recent reading of the specified measurement,
    and an older reading of the same measurement.
    Routine reads the log looking for the older reading.

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
    current = measure(meas_as_index(meas_label), READING_LAST)

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

    result = current.value - oldest_reading.value

    if (result < 0.0) and (not allow_negative):
        # If the difference is negative, the measurement has been reset.
        result = current.value

    return result


@MEASUREMENT
def precip_2_hour(inval):
    # Rain during the last 2 hours
    # Requires a precip accumulation measurement labeled "RAIN ACCU"

    # Compute rainfall during the period
    rainfall = differential_reading("RAIN ACCU", 2*3600, False)

    # Read the threshold from the setup
    threshold = general_read_value("Rain 2h")

    # A threshold of zero means do not trigger
    if threshold > 0:
        # Is the rainfall heavy enough to trigger the sampler?
        if rainfall > general_read_value("Rain 2h"):
            if trigger_sampler():
                # Write a log entry indicating why sampler was triggered.
                reading = Reading(label="Rain2h Trig", time=time_scheduled(),
                                  etype='E', value=rainfall, quality='G')
                reading.write_log()

    return rainfall


@MEASUREMENT
def precip_24_hour(inval):
    # Just like precip_last_2_hour, but over a 24 hour period
    rainfall = differential_reading("RAIN ACCU", 24 * 3600, False)

    threshold = general_read_value("Rain 24h")
    if threshold > 0:
        if rainfall > threshold:
            if trigger_sampler():
                reading = Reading(label="Rain24h Trig", time=time_scheduled(),
                                  etype='E', value=rainfall, quality='G')
                reading.write_log()

    return rainfall


"""Stage section is below"""


def enough_water():
    """
    Routine checks the last stage reading and returns True
    if there is enough water to trigger the sampler.
    """

    # Check the current stage.  Requires a measurement labeled "STAGE".
    stage = measure("STAGE", READING_LAST)

    # Read the threshold from the setup
    threshold = general_read_value("Stage Limit")

    # A threshold of zero means the threshold is not required
    if threshold == 0:
        return True
    elif stage.value > threshold:  # crossed the threshold?
        return True
    else:
        return False


@MEASUREMENT
def stage_sampling(inval):
    """ Routine is associated with the stage measurement.
    If the stage changes rapidly, we want to trigger the sampler
    """

    # Find out the measurement interval for stage
    stage_interval_text = setup_read("M{} Meas Interval".format(index()))
    stage_interval_sec = sl3_hms_to_seconds(stage_interval_text)

    # Find the difference in two stage readings
    stage_change = differential_reading(meas_find_label(index()), stage_interval_sec, True)

    # Rapid up check
    threshold = general_read_value("Rapid Up")
    if threshold != 0.0:  # A setup of zero means threshold is disabled
        if stage_change > threshold:
            if trigger_sampler():
                # write a log entry
                reading = Reading(label="Rapid Up", time=time_scheduled(),
                                  etype='E', value=stage_change, quality='G')
                reading.write_log()

    # Rapid down check
    threshold = general_read_value("Rapid Down")
    if threshold != 0.0:  # A setup of zero means threshold is disabled
        if (-stage_change) > threshold:  # Note the negative sign
            if trigger_sampler():
                # Write a log entry indicating why sampler was triggered.
                reading = Reading(label="Rapid Down", time=time_scheduled(),
                                  etype='E', value=stage_change, quality='G')
                reading.write_log()

    return inval  # Return the untouched stage reading


"""Threshold based sampling is below"""

# Multiple thresholds may be setup.
# As each thresholds is crossed, the next one becomes relevant.
# If losing count on reboot is of concern, this could be stored in the general purpose settings.
threshold_index = 1

# How many triggers are in the system
# This could also be stored in the general purpose settings if it varies from station to station.
threshold_count = 8


def threshold_get_current():
    """
    Returns the value of the next trigger.
    """
    setting_name = "Threshold {}".format(threshold_index)
    return general_read_value(setting_name)


def threshold_move():
    """ Increments the value of the current trigger"""
    global threshold_index
    threshold_index += 1
    if threshold_index > threshold_count:
        threshold_index = 1


@MEASUREMENT
def threshold_sampler(inval):
    """This is traditionally hooked into the turbidity measurement.
    If the stage is high enough, check the two most recent readings
        of this measurement.
    If both cross the relevant threshold, the sampler may be triggered."""

    sample_now = False
    if enough_water():  # we may not trigger unless the stage is high enough
        threshold = threshold_get_current()

        # verify the threshold is not zero and see if threshold has been crossed
        if threshold > 0.0:
            if inval > threshold:

                # find the previous reading of this measurement in the log
                time_previous = time_scheduled() - 1  # anything older than current reading
                meas_label = meas_find_label(index())

                # find out this measurement's interval to compute time of previous
                interval_text = setup_read("M{} Meas Interval".format(index()))
                interval_sec = sl3_hms_to_seconds(interval_text)

                try:
                    previous_reading = Log(oldest=time_previous - interval_sec,
                                           newest=time_previous,
                                           match=meas_label).get_newest().value

                except LogAccessError:
                    previous_reading = 0.0

                # if we find a previous reading, and it is also over the threshold, sample now
                if previous_reading > threshold:
                    sample_now = True

    if sample_now:
        if trigger_sampler():  # the sampler did trigger
            threshold_move()  # the next threshold is now relevant
            # Write a log entry indicating why sampler was triggered.
            reading = Reading(label="ThreshTrig", time=time_scheduled(),
                              etype='E', value=inval, quality='G')
            reading.write_log()

    return inval  # return the unmodified reading no matter whether we sampled


@TASK
def periodic_sampler():
    """Function triggers sampler on a user set schedule"""
    if enough_water():  # we may not trigger unless the stage is high enough
        if trigger_sampler(): # we triggered it
            # Write a log entry indicating why sampler was triggered.
            reading = Reading(label="PeriodTrig", time=time_scheduled(),
                              etype='E', quality='G')
            reading.write_log()


@TASK
def manual_sampler():
    """Function triggers the sampler.
    Intended to be manually triggered to ensure sampler is working."""
    if not is_being_tested():
        trigger_sampler_master()
        # Write a log entry indicating why sampler was triggered.
        reading = Reading(label="TrigManual", time=time_scheduled(),
                          etype='E', quality='G')
        reading.write_log()

