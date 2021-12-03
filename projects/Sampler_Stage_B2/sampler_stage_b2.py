"""
    Program triggers an Isco sampler based on stage, time, and bottle count
    There is a setup file associated with this script sampler_stage_b2_setup.txt

    Principle of operation:
        Stage is periodically measured
        If the current stage reading exceeds a user set threshold,
        And if enough time has passed since the last sampler trigger,
        And if there are enough bottles left in the sampler,
        The sampler is triggered (Digital output 1 pulse for 5 sec)

        The amount of time needed between sampler triggers is dependent on
        the current bottle count

    There are several General Purpose Variables that control the script:
    GP1 HighThreshold - the stage threshold for triggering the sampler
    GP2 InitialIntervalMin - the interval that must pass between triggers
        if the bottle count is less than GP5 BottleSwitch
    GP3 LateIntervalMin - ditto but if bottle count is greater than GP5
    GP4 BottleCapacity - how many vials the sampler holds
    GP5 BottleSwitch - at what bottle count the system should switch intervals

    GP10 TestMode - set to 1 to run dry tests on the system

    The system also supports sending SMS messages if the bottle count runs low,
    but it is disabled by default
    Please see /projects/Sampler_Turbidity_B2 for a description of the SMS feature

    Bottle count may be reset via script task S1.
    Bottle count will be reset to 0 on power up.
    Sampler may be triggered via script task S2
"""

from sl3 import *

# We count how many bottles are in use.  If losing count on reboot is of concern,
# this could be stored in the general purpose settings.
bottles_used = 0

# Time sampler was triggered last.
time_last_trigger = 0.0

# stage at last trigger
value_last_trigger = 0.0

# the most recent stage reading
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
    global value_last_meas

    # add diagnostic info to the script status
    message = ("Bottles used: {}/{:.0f}\n".format(bottles_used, float(setup_read("GP4 value"))))
    if bottles_used >= 1:
        message += ("Last trigger: {}\n".format(ascii_time(time_last_trigger)))
        message += ("Stage was: {}\n".format(value_last_trigger))
    else:
        message += "Not triggered since reset\n"
    message += ("Current stage: {}\n".format(value_last_meas))
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

    bottles_used = 0
    time_last_trigger = 0.0
    value_last_trigger = 0.0

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

    print(status_update())


def trigger_sampler_attempt(time_stamp):
    """
    Call to attempt to trigger the sampler.
    Certain conditions may prevent the triggering.

    :return: True if sampler was triggered.
    """
    global bottles_used
    global time_last_trigger

    bottles_capacity = float(setup_read("GP4 value"))
    bottle_switch = float(setup_read("GP5 value"))
    if bottles_used >= bottle_switch:
        deadtime_seconds = float(setup_read("GP3 value")) * 60  # Late interval
    else:
        deadtime_seconds = float(setup_read("GP2 value")) * 60  # Initial interval

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


"""
# to test, set GP10 "TestMode" to 1 or greater ( set to less than 1 to end test mode)
# in this mode, instead of measuring a real sensor
# the system sequentially pulls sensor data from the list below
"""
test_value = [1.00, 1.21, 1.40, 2.02, 2.58, 2.86,
              3.42, 3.99, 4.56, 5.00, 5.44, 5.88,
              5.77, 5.45, 5.76, 5.78, 6.01, 6.12,
              6.32, 6.76, 7.20, 7.44, 6.00, 4.56,
              3.12, 1.68, 1.55, 1.50, 1.32, 0.99]
test_index = 0


@MEASUREMENT
def stage_check(stage):
    """
    This function should be connected to the stage measurement
    When invoked, it will decide whether to trigger the sampler
    """
    global time_last_trigger
    global value_last_meas

    # test mode - see test_value
    if float(setup_read("GP10 value")) >= 1.0:
        global test_value
        global test_index
        stage = test_value[test_index]
        test_index += 1
        if test_index >= len(test_value):
            test_index = 0

    value_last_meas = stage

    # we use the time the measurement was SCHEDULED rather than real time
    # to ensure computations are not affected by system delays
    time_stamp = time_scheduled()

    # make sure time_last_trigger is not 0
    # otherwise baseline triggers on first measurement after bootup
    if time_last_trigger == 0.0:
        time_last_trigger = time_stamp

    triggered = False
    if stage > float(setup_read("GP1 value")):
        if trigger_sampler_attempt(time_stamp):
            triggered = True

    if triggered:
        global value_last_trigger
        value_last_trigger = stage

    print(status_update())
    return stage


@TXFORMAT
def sms_format(ignored):
    """
    Triggers when system sends a SMS message via telemetry
    SMS will have the last script status
    """
    return status_update()
