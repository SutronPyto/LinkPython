"""
    Program triggers an Isco sampler based on turbidity and time
    There is a setup file associated with this script sampler_b2_setup.txt
    The complete documentation is in sampler_b2_readme.pdf

"""

from sl3 import *

# We count how many bottles are in use.  If losing count on reboot is of concern,
# this could be stored in the general purpose settings.
bottles_used = 0

# Time sampler was triggered last.
time_last_trigger = 0.0

# Turbidity at last trigger
value_last_trigger = 0.0

# the reason for last triggering the sampler
trigger_cause = ""

# the most recent turbidity reading
value_last_meas = 0.0


def status_update():
    """
    Provides status that can be read in the Scripts tab of LinkComm
    :return: human readable status
    :rtype: str
    """
    global bottles_used
    global time_last_trigger
    global value_last_trigger
    global trigger_cause
    global value_last_meas

    # add diagnostic info to the script status
    message = ("Bottles used: {}/{:.0f}\n".format(bottles_used, float(setup_read("GP6 value"))))
    if trigger_cause != "":
        message += ("Last trigger: {}\n".format(ascii_time(time_last_trigger)))
        message += ("Because: {}\n".format(trigger_cause))
        message += ("Turbidity was: {}\n".format(value_last_trigger))
    else:
        message += "Not triggered since reset\n"
    message += ("Current turbidity: {}\n".format(value_last_meas))
    return message


@MEASUREMENT
def bottles_used_meas(ignored):
    """ returns the number of bottles used"""
    return float(bottles_used)


@TASK
def clear_bottle_count():
    """ clears the number of bottles used and other trackers"""
    global bottles_used
    global time_last_trigger
    global value_last_trigger
    global trigger_cause

    bottles_used = 0
    time_last_trigger = 0.0
    value_last_trigger = 0.0
    trigger_cause = ""

    # write a log entry
    reading = Reading(label="BottleClear", time=utime.time(), etype='E')
    reading.write_log()

    print(status_update())


def trigger_sampler_master(time_stamp):
    """triggers sampler, updates trackers"""

    # increment the number of bottles used
    global bottles_used
    bottles_used += 1

    # update the time of the last trigger
    global time_last_trigger
    time_last_trigger = time_stamp

    # trigger sampler by pulsing output
    output_control('OUTPUT1', True)
    utime.sleep(5)
    output_control('OUTPUT1', False)

    # write a log entry
    reading = Reading(label="Triggered",
                      time=time_stamp,
                      etype='E',
                      value=bottles_used,
                      right_digits=0,
                      quality='G')
    reading.write_log()


@TASK
def trigger_sampler_now():
    """ tie this to a script task to manually trigger the sampler"""
    trigger_sampler_master(utime.time())

    global trigger_cause
    trigger_cause = "User"

    print(status_update())


def trigger_sampler_attempt(time_stamp):
    """
    Call to attempt to trigger the sampler.
    Certain conditions may prevent the triggering.

    :return: True if sampler was triggered.
    """
    bottles_capacity = float(setup_read("GP6 value"))
    deadtime_seconds = float(setup_read("GP3 value")) * 3600
    global bottles_used
    global time_last_trigger

    trigger = True

    if bottles_used >= bottles_capacity:
        trigger = False  # out of bottles
    elif time_stamp - time_last_trigger < deadtime_seconds:
        trigger = False  # too soon since last
    elif is_being_tested():
        trigger = False  # script is being tested

    if trigger:
        trigger_sampler_master(time_stamp)  # Call routine that controls sampler.
        return True

    else:
        return False  # Sampler was NOT triggered.


def baseline_check(time_stamp):
    """
    Is it time for a baseline sampler trigger?
    """
    baseline_interval_sec = float(setup_read("GP1 value")) * 3600
    time_diff_sec = time_stamp - time_last_trigger
    if time_diff_sec >= baseline_interval_sec:
        if trigger_sampler_attempt(time_stamp):
            # sampler triggered
            global trigger_cause
            trigger_cause = "Baseline"

            # write event to log
            Reading(label=trigger_cause,
                    time=time_stamp,
                    etype='E',
                    value=time_diff_sec,
                    right_digits=0,
                    units="sec",
                    quality='G').write_log()
            return True

    return False


def change_since_last_trigger_check(current_turbidity, time_stamp):
    """
    Should we trigger based on current turbidity and last turbidity?
    """
    global value_last_trigger
    diff = current_turbidity - value_last_trigger

    limit = float(setup_read("GP2 value"))
    if abs(diff) >= limit:
        if trigger_sampler_attempt(time_stamp):
            # sampler triggered
            global trigger_cause
            trigger_cause = "Change since last trigger"

            # write event to log
            Reading(label="ChangeSince",
                    time=time_stamp,
                    etype='E',
                    value=diff,
                    right_digits=0,
                    quality='G').write_log()
            return True

    return False


def high_threshold_check(current_turbididty, time_stamp):
    """
    Trigger based on high threshold?
    """
    threshold = float(setup_read("GP4 value"))
    if current_turbididty >= threshold:
        # turbidity is high enough
        # but has it been long enough since last sample?
        global time_last_trigger
        time_diff_sec = time_stamp - time_last_trigger
        time_interval = float(setup_read("GP5 value")) * 3600

        if time_diff_sec >= time_interval:
            if trigger_sampler_attempt(time_stamp):
                # sampler triggered
                global trigger_cause
                trigger_cause = "Threshold"

                # write event to log
                Reading(label=trigger_cause,
                        time=time_stamp,
                        etype='E',
                        value=time_diff_sec,
                        right_digits=0,
                        units="sec",
                        quality='G').write_log()
                return True

    return False


"""
# to test, set GP10 "Test Mode" to 1 or greater ( set to less than 1 to end test mode)
# in this mode, instead of measuring a turbidity sensor
# the system sequentially pulls 'turbidity' data from the list below
# a list of simulated turbidity values used for testing
"""
"""
test_turbidity = [100, 150,7 201, 180,
                  200, 210, 211, 209,
                  222, 223, 229, 230,
                  500, 750, 901, 902,
                  2000, 2001, 2002, 2003,
                  2006, 2008, 2009, 2001,
                  1500, 1200, 800, 501,
                  450, 400, 350, 300,
                  250, 203, 151, 103]
"""
test_turbidity = [0 , -1, 180, 181, 190, 191, 185, 192, 199,
                  201, 222, 233, 580, 790, 2900, 2999, 3001,
                  3008, 3008, 3009, 3010, 3100, 2900, 2998,
                  800, 700, 600, 500, 400, -1, 0, 180, 190]
test_index = 0


@MEASUREMENT
def turbidity_check(turbidity):
    """
    This function should be connected to the turbidity measurement
    When invoked, it will decide whether to trigger the sampler
    """
    global trigger_cause
    global time_last_trigger
    global value_last_meas

    # test mode - see test_turbidity
    if float(setup_read("GP4 value")) >= 1.0:
        global test_turbidity
        global test_index
        turbidity = test_turbidity[test_index]
        test_index += 1
        if test_index >= len(test_turbidity):
            test_index = 0

    value_last_meas = turbidity

    # we use the time the measurement was SCHEDULED rather than real time
    # to ensure computations are not affected by system delays
    time_stamp = time_scheduled()

    # make sure time_last_trigger is not 0
    # otherwise baseline triggers on first measurement after bootup
    if time_last_trigger == 0:
        time_last_trigger = time_stamp

    triggered = False
    if change_since_last_trigger_check(turbidity, time_stamp):
        triggered = True
    elif high_threshold_check(turbidity, time_stamp):
        triggered = True
    elif baseline_check(time_stamp):
        triggered = True

    if triggered:
        global value_last_trigger
        value_last_trigger = turbidity

    print(status_update())
    return turbidity


@TXFORMAT
def sms_format(ignored):
    """
    Triggers when system sends a SMS message via telemetry
    SMS will have the last script status
    """
    return status_update()
