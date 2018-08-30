# Example:  demonstrates custom logging based on an event trigger

from sl3 import *


def _log_task_trigger(task_trig):
    import utime

    reading = Reading(value=1.0, label=task_trig, time=utime.time())
    reading.write_log()


@TASK
def log_task_trigger():
    """
    Record log entry of task triggering script.

    The label in the log will be script number and the trigger type with a value of 1.0.
        * Example 1: S2 Schedule
        * Example 2: S3 Boot
    Multiple scripts can be setup with the same task but with different triggers.
    """
    _log_task_trigger("S" + str(index()) + " " + command_line("!S" + str(index()) + " trigger").strip())