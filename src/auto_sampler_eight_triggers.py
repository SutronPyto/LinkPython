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

    For this application, please note that     
    the trigger points must be such that they are increasing up to a peak point 
    after which they are decreasing.  An example of such trigger points would be 
    [1.1, 2.1, 3.1, 4.1, 3.2, 2.2, 1.2]
"""

general_stub = {
    "Threshold 1": 1.0,
    "Threshold 2": 2.0,
    "Threshold 3": 3.0,
    "Threshold 4": 4.0,
    "Threshold 5": 5.0,
    "Threshold 6": 4.6,
    "Threshold 7": 3.7,
    "Threshold 8": 2.2,
    "Threshold Reset": 0.5,
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
    if sutron_link:  # do not wait on PC (slows test down)
        utime.sleep(2.0)
    power_control('SW2', False)

    # write a log entry
    reading = Reading(label="Triggered", time=time_scheduled(),
                      etype='E', value=bottles_used, units="btl",
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

    # should we trigger?
    trigger = True

    if bottles_used >= bottles_capacity:
        trigger = False  # out of bottles

    elif sutron_link:  # running on embedded system - we don't want these checks on PC
        if (utime.time() - time_last_sample) < min_time_between_samples:
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
def stage_sampling(stage):
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

    return stage  # Return the untouched stage reading


"""
Threshold based sampling is below

The thresholds must  be such that they are increasing up to a peak point after which they are decreasing.
An example of such thresholds: 
[1.1, 2.1, 3.1, 4.1, 3.2, 2.2, 1.2]

For the ascending points (points 1.1, 2.1, 3.1 and 4.1), the system will trigger the sampler 
    if two consecutive turbidity readings exceed the threshold. 
For the descending points (points 3.2, 2.2, 1.2), 
    the system will trigger if the two values are below the threshold. 

As each thresholds is crossed, the next one becomes relevant.  If the next threshold is 
beyond the triggering value, it is automatically crossed too.

For example (using the thresholds above), if the initial values were 3.3, the system would
trigger the sampler and then move to threshold 4.1

Once all the trigger points have been achieved, 
the system will no longer trigger the sampler until the threshold reset 

Threshold reset:
Once the turbidity value reads below a user set ‘threshold reset’ value, 
the system will reset the triggering program.  At this point, the sampler may be triggered 
as if the program had just started.  The bottle counter is unaffected by this reset.

"""

# The currently relevant threshold
threshold_index = 1

# How many triggers are in the system
# This could also be stored in the general purpose settings if it varies from station to station.
threshold_count = 8

# Is the system tracking ascending or descending?
threshold_ascending = True

# Have we hit all the threshold points?  If so we cannot sample any more and are 'locked'.
threshold_locked = False

# What was the previous turbidity reading?  Negative value means we do not have a previous reading.
previous_reading = -1.0


def threshold_reset():
    """Resets the global threshold values"""
    global threshold_index
    global threshold_ascending
    global threshold_locked
    global previous_reading

    threshold_index = 1
    threshold_ascending = True
    threshold_locked = False
    previous_reading = -1.0


def threshold_get_value(indexi):
    """
        Returns the value of the threshold associated with the index.
    """

    global threshold_count

    if not threshold_locked:
        setting_name = "Threshold {}".format(indexi)
        return general_read_value(setting_name)
    elif indexi > threshold_count:
        return 0.0  # use zero to mean no valid threshold
    else:
        return 0.0  # use zero to mean no valid threshold


def threshold_check(current_turbidity):
    """
    Checks the current and previous turbidity readings against the threshold
    Must be called by @MEASUREMENT function

    :param current_turbidity: the current turbidity reading
    :type current_turbidity: float
    :return: True if the threshold has been crossed
    :rtype: bool
    """

    global previous_reading
    global threshold_index
    global threshold_locked

    # has the current threshold been crossed?
    threshold_crossed = False

    # have we reached all the turbidity points? if so we cannot trigger
    if not threshold_locked:

        # get the previous reading
        if previous_reading > 0.0:  # negative value means we don't have a previous reading

            # get the current threshold
            threshold = threshold_get_value(threshold_index)

            # verify the threshold is not zero and see if threshold has been crossed
            if threshold > 0.0:
                if threshold_ascending:  # if ascending, value must be greater than threshold
                    if current_turbidity > threshold:
                        if previous_reading > threshold:
                            threshold_crossed = True
                else:  # if descending, value must be less than threshold
                    if current_turbidity < threshold:
                        if previous_reading < threshold:
                            threshold_crossed = True

    return threshold_crossed


def threshold_move_low(current_trubidity):
    """
    Moves to the next relevant turbidity threshold
    It may skip thresholds if the current turbidity value is right
    Changes the ascending/descending quality if appropriate

    :param current_trubidity:
    :type current_trubidity:
    :return:
    :rtype:
    """

    global threshold_index
    global threshold_locked
    global threshold_ascending

    skip = False  # can we skip a threshold?

    if not threshold_locked:
        # is there a next threshold?  if not, go into locked mode (no more triggers)
        next_threshold_index = threshold_index + 1
        if next_threshold_index > threshold_count:
            threshold_locked = True

        else:
            # can we switched from ascending to descending?
            switched_to_descending = False
            if threshold_ascending:
                # compare current threshold value to the next to see if we went
                # from ascending to descending

                this_threshold = threshold_get_value(threshold_index)
                next_threshold = threshold_get_value(next_threshold_index)

                if next_threshold < this_threshold:
                    threshold_ascending = False
                    switched_to_descending = True

            # now that we've decided on ascending/descending, increment to the next point
            threshold_index += 1

            # unless we switched to descending, see if we need to skip any threshold points
            if not switched_to_descending:
                if threshold_check(current_trubidity):
                    # yes we can skip the next point
                    skip = True

    return skip


def threshold_move(current_turbidity):
    """
    Moves to the next relevant turbidity threshold
    It may skip thresholds if the current turbidity value is right
    Changes the ascending/descending quality if appropriate

    Wraps threshold_move_low, allowing us to skip multiple thresholds at once

    :param current_turbidity: current turbidity value
    :type current_turbidity: float
    """

    while not threshold_locked:
        if not threshold_move_low(current_turbidity):
            break  # we did not skip a turbidity point and we are done with loop


@MEASUREMENT
def threshold_sampler(turbidity):
    """This is traditionally hooked into the turbidity measurement.
    If the stage is high enough, check the two most recent readings
        of this measurement.
    If both cross the relevant threshold, the sampler may be triggered."""

    global previous_reading

    sample_now = False
    if enough_water():  # we may not trigger unless the stage is high enough

        # first check is for turbidity being low enough for a reset
        reset_limit = general_read_value("Threshold Reset")
        if (turbidity <  reset_limit) and (previous_reading < reset_limit):
            threshold_reset()  # we have gone below the reset value
            # Write a log entry indicating the reset
            reading = Reading(label="ThreshReset", time=time_scheduled(),
                              etype='E', value=turbidity, quality='G')
            reading.write_log()

        # if we did not reset, do the threshold check
        elif threshold_check(turbidity):  # have we crossed the threshold?
            sample_now = True

    if sample_now:
        if trigger_sampler():  # the sampler did trigger
            threshold_move(turbidity)  # the next threshold is now relevant

            # Write a log entry indicating why sampler was triggered.
            reading = Reading(label="ThreshTrig", time=time_scheduled(),
                              etype='E', value=turbidity, quality='G')
            reading.write_log()

    # update the previous reading
    update = True

    # on the embedded system, we only want to use scheduled readings
    if sutron_link:
        if is_scheduled():
            previous_reading = turbidity
    else: # to allow testing on PC, we need to allow any reading as last
        previous_reading = turbidity

    return turbidity  # return the unmodified reading no matter whether we sampled


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



""" 
Below is test code used to verify the correct workings of
    the turbidity sampler trigger algorithm.
This test is meant ot run on the PC only.
Running the routine auto_eight_test will output logged data that
    will indicate how the system responds to turbidity input
"""

# these are the values that we will feed into the turbidity tester
turbidity_list = [1.0,
                  1.5,
                  1.0,
                  1.6,
                  1.6,
                  1.8,
                  1.8,
                  2.5,
                  1.8,
                  2.6,
                  1.8,
                  2.7,
                  2.7,
                  2.8,
                  4.2,
                  4.2,
                  4.3,
                  4.4,
                  3.2,
                  3.2,
                  5.5,
                  5.9,
                  5.8,
                  0.0,
                  5.9,
                  3.0,
                  3.0,
                  100.0,
                  123.123,
                  2.0,
                  2.0,
                  0.1,
                  0.2,
                  1.6,
                  1.6,
                  1.8,
                  1.8,
                  2.5,
                  1.8,
                  2.6,
                  2.6,
                  2.6,
                  2.6,
                  2.6,
                  2.6,
                  1.0,
                  1.0,
                  1.0,
                  3.8,
                  3.9,
                  4.4,
                  4.7,
                  ]


def auto_eight_test():
    """Test routine"""
    if sutron_link:
        raise Exception("These are tests meant to run on PC")

    """write a log entry to separate from chaff"""
    reading = Reading(label="START TURBIDITY",
                      time=utime.time(),
                      quality='G')
    reading.write_log()

    """Run the values in the table through the turbidty sampling algorithm"""
    for turbidity in turbidity_list:
        # log the turbidity reading first
        reading = Reading(label="Turbidity",
                          etype='M',
                          value=turbidity,
                          time=utime.time(),
                          quality='G')
        reading.write_log()

        # next, throw the reading into the sampler script
        threshold_sampler(turbidity)

    """
    Print the log out, starting with oldest
    and limiting to a reasonable number.
    This is meant for running on the PC"""
    for reading in Log(count = 1000, pos = LOG_OLDEST):
        print(reading)

