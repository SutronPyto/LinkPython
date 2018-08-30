# Example:  demonstrates triggering a digital output based on a tipping bucket level

from sl3 import *
import utime


@MEASUREMENT
def bucket_empty(inval):
    """Routine is tied into a measurement that samples a weighing bucket.
    Once reading exceeds limit, open valve, wait a bit, close the valve"""

    limit = 12.5
    if inval > limit:
        output_control('OUTPUT2', True)
        utime.sleep(3)
        output_control('OUTPUT2', False)

        # write a log entry
        reading = Reading(label="Emptied", time=time_scheduled(), etype='E')
        reading.write_log()

    return inval


@TASK
def trigger_sampler():
    """Checks last readings of M1 and M2.  If readings meet conditions,
    sampler is triggered via a digital output"""

    if (measure(1).value > 32.5):
        if (measure(2).value < 13.9):
            # trigger sampler by pulsing output for 500ms
            output_control('OUTPUT1', True)
            utime.sleep(0.5)
            output_control('OUTPUT1', False)

            # write a log entry
            reading = Reading(label="Triggered", time=utime.time(), etype='E')
            reading.write_log()
