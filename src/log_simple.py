# Example:  demonstrates log access

from sl3 import *


def log_write_example():
    """
    Writes a log entry
    """

    # first, create a reading with all the details
    r = Reading(time=utime.time(),  # use current time
                label="stage",
                value=12.53,
                units="ft",
                quality="G",
                right_digits=2,
                etype="M")

    # then write it to the log
    r.write_log()


def log_read_entry():
    """
    Searches the log for 10 log entries with a specific label.
    """

    try:
        # try statement is needed in case the log entry does not exist
        # setup the log search and get the 10 newest readings
        for r in Log(match="stage", count=10, pos=LOG_NEWEST):
            print(r)

    except LogAccessError:
        # we did not find all the entries we expected
        print("log entry not found")


def log_compute_diff():
    """
    Returns the difference between the last two stage log entries
    """
    try:
        # setup the log search
        l = Log(match="stage", count=2, pos=LOG_NEWEST)

        # get the values of the two newest readings
        s1 = l.get_newest().value
        s2 = l.get_older().value

        # compute the diff
        return abs(s1 - s2)

    except LogAccessError:
        # we did not find all the entries we expected
        return 0


def log_time_bound_meas():
    """
    Reads all logged measurements from the last 15 minutes
    and packs them into a string
    """
    # we will format up all log entries in here
    formatted = ""

    # create the timestamps
    time_now = utime.time()  # current time
    time_end = time_now - 15 * 60  # 15 min ago

    try:
        for r in Log(oldest=time_end, newest=time_now):
            if r.etype == 'M':  # measurements only
                formatted += str(r)
                formatted += '\r\n'

    except LogAccessError:
        # we did not find all the entries we expected
        formatted = "No entries found"

    return formatted


def log_look_for_bad_data():
    """
    Parses log data looking for bad entries.
    Returns the number of bad entries found.
    """
    bad = 0  # how many bad entries found?

    try:
        for r in Log(count=1000):
            if r.quality == 'B':
                bad += 1
                print(r)

    except LogAccessError:
        # we did not find any logged data
        pass

    return bad
