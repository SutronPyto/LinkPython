# Example:  Triggers sampler based on volume

"""
* Sampler is triggered based on water volume.
* If volume is insufficient, triggers sampler at 20:00:00 UTC
* Sampler triggers no more than once per day.

There is a setup file associated with this script!
"""

from sl3 import *
import utime

# We remember the total volume
g_volume_total = 0.0

# The sampler has a limited number of bottles.
bottles_capacity = 24

# We count how many bottles are in use.
bottles_used = 0

# Time sampler was triggered last.
time_last_sample = 0.0


def triggered_today():
    """Have we triggered the sampler today?"""
    if time_last_sample == 0.0:
        return False  # we never triggered
    else:
        # what is the day today?
        today = utime.localtime()[6]  # returns the weekday (value from 0 to 6)

        # and what day did we last trigger?
        last = utime.localtime(time_last_sample)[6]

        if today == last:
            return True  # yes we triggered today
        else:
            return False


def trigger_sampler_master():
    """Triggers the sampler immediately and logs it."""

    global bottles_used
    global time_last_sample

    # increment the number of bottles used
    bottles_used += 1

    # update the time of the last trigger
    time_last_sample = utime.time()

    # clear the total volume
    global g_volume_total
    g_volume_total = 0.0

    # trigger sampler by pulsing output for 5 seconds
    power_control('SW2', True)
    utime.sleep(5.0)
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

    trigger = True

    if bottles_used >= bottles_capacity:
        trigger = False  # out of bottles
    elif triggered_today():
        trigger = False  # already triggered today
    elif is_being_tested():
        trigger = False  # script is being tested
    elif setup_read("Recording").upper() == "OFF":
        trigger = False  # if recording is off, do not sample

    if trigger:
        trigger_sampler_master()  # Call routine that controls sampler.
        return True

    else:
        return False  # Sampler was NOT triggered.


@TASK
def daily_trigger():
    """
    This function should be associated with a script task scheduled for a certain time every day.
    If the sampler has not been triggered today, this function will trigger it.
    """

    if trigger_sampler():
        # sampler was triggered

        global g_volume_total

        # Write a log entry indicating why sampler was triggered.
        reading = Reading(label="DailyTrig", time=time_scheduled(),
                          etype='E', value=g_volume_total, quality='G')
        reading.write_log()


def volume_threshold():
    """
    Returns the threshold at which the volume difference triggers the sampler.
    It is stored in the setup as Alarm 1 Threshold.

    :return: volume threshold
    :rtype: float
    """
    setup_str = setup_read("M{} Alarm 1 Threshold".format(index()))
    return float(setup_str)


@MEASUREMENT
def compute_volume_total(inval):
    """
    This function needs to be associated with the total volume measurement.
    It will compute the total volume based on the current volume and past volume.
    The script will trigger the sampler if appropriate.

    :param inval: not relevant
    :return: the current volume reading

    """

    global g_volume_total

    # update total volume and store it in a local variable
    # in case we need to clear g_volume_total
    if is_scheduled():  # do not tally volume unless this is a scheduled measurement
        g_volume_total += measure("VOLUME").value  # update total volume

    local_total = g_volume_total  # copy to a local variable

    # if the volume is high enough, trigger sampler
    if local_total > volume_threshold():
        if trigger_sampler():
            # sampler was triggered

            # Write a log entry indicating why sampler was triggered.
            reading = Reading(label="VolumeTrig", time=time_scheduled(),
                              etype='E', value=local_total, quality='G')
            reading.write_log()

    # add diagnostic info to the script status
    print("Bottles used: {}".format(bottles_used))
    print("Bottle capacity: {}".format(bottles_capacity))
    if time_last_sample:
        print("Last trigger: {}".format(ascii_time(time_last_sample)))
        if triggered_today():
            print("   Which was today")
        else:
            print("   No trigger today")
    else:
        print("Not triggered since bootup")

    return local_total  # return the total volume (before clearing it)
