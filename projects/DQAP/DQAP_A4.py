""" DQAP processing

    All credit to Derek Young at the University of Hawaii <dereky@hawaii.edu>

    DQAP is an algorighm used by NOS to measure ocean levels.
    DQAP computes a mean and a standard deviation accross multiple samples.
    The mean and standard deviation are used to eliminate outliers.
    The rest of the samples are averaged into a final ocean level reading.

    There is a Satlink setup associated with this script.
    In that setup, M1 (sensor samp) is a measuremnt setup to sample the sensor.
        The result of M1 is the raw data from the sensor from which we compute DQAP.
    M2 (sensor DQAP) is the final level result of the DQAP - it is the water level.
    The rest of the measurements are artifacts of the DQAP equation which are
        useful to verify DQAP is working as expected.
"""

from sl3 import *
from math import sqrt

# sensor data gets put into this list
raw_vals = []

# initial condition handler.  set to True after 1st DQAP interval
is_started = 0

# the results of the computation are stored here
mean = 0.0
stdev = 0.0
dqap = 0.0
num_dqap_samples = 0
dqap_quality = 0


def start():
    """ sets is_started.  used for testing"""
    global is_started
    is_started = True


def reset_results():
    """ resets the computation results"""
    global mean, stdev, dqap, num_dqap_samples, dqap_quality

    mean = 0.0
    stdev = 0.0
    dqap = 0.0
    num_dqap_samples = 0
    dqap_quality = 0


def print_status():
    """ Updates the script status """
    global mean, stdev, dqap, num_dqap_samples, dqap_quality

    print("mean = " + str(mean))
    print("standard deviation = " + str(stdev))
    print("DQAP value = " + str(dqap))
    print("num_dqap_samples = " + str(num_dqap_samples))
    print("dqap_quality = " + str(dqap_quality))


@MEASUREMENT
def get_data(val):
    """ This measurement samples the sensor.  
    The sensor data is stored in the list."""
    global raw_vals, is_started

    """ 
    prevent get_data() and create_dquap() stepping on each other
    lock() means only this thread may execute right now
    """
    lock()

    if is_started:
        raw_vals.append(val)

    unlock()  # MUST unlock after locking.  othrewise, no other script could ever run

    return val


@MEASUREMENT
def create_dqap(val):
    """
    Call to process the sensor data in raw_vals.
    Produces all DQAP results and stores them globals.
    Returns DQAP processed sensor result
    Initial call to this routine will not produce a result.
    """
    global raw_vals, dqap_vals, mean, stdev, dqap, num_dqap_samples, dqap_quality, is_started

    dqap_raw_vals = []  # we will copy the raw samples here
    dqap_vals = []  # the good samples go here

    """ 
    prevent get_data() and create_dquap() stepping on each other
    lock() means only this thread may execute right now
    """
    lock()

    # initial condition.  all data prior to the first call is invalid
    if not is_started:
        reset_results()
        was_started = False
        is_started = True  # this starts sensor data collection

    else:
        was_started = True
        dqap_raw_vals = raw_vals[:]  # copy the data collected from the sensor into a new list
        raw_vals.clear()  # clear out sensor data so it can be refilled form start

    # MUST unlock after locking.  othrewise, no other script could ever run
    unlock()

    if not was_started:  # initial condition
        return 0.0

    # how many samples do we have?
    num_raw_samples = len(dqap_raw_vals)

    if num_raw_samples == 0:  # no samples.  do not compute (prevent divide by zero)
        reset_results()

    else:
        # compute mean
        mean = sum(dqap_raw_vals) / num_raw_samples

        # compute standard deviation
        variance = sum([(e - mean) ** 2 for e in dqap_raw_vals]) / num_raw_samples
        if variance > 0.0:
            stdev = sqrt(variance)
        else:
            stdev = 0.0

        # compute DQAP value
        if stdev == 0:
            dqap = mean
            num_dqap_samples = 0

        else:
            # eliminate outliers
            for meas in dqap_raw_vals:
                if (meas < mean + 3 * stdev) and (meas > mean - 3 * stdev):
                    dqap_vals.append(meas)

            # if we have good vlaues, compute result
            if dqap_vals:
                num_dqap_samples = len(dqap_vals)
                dqap = sum(dqap_vals) / num_dqap_samples
            else:
                num_dqap_samples = 0
                dqap = 0.0

        # quality is good if half the samples are not outliers
        if num_dqap_samples < (num_raw_samples / 2):
            dqap_quality = 0
        else:
            dqap_quality = 1

    print_status()

    return float(dqap)


""" 
The set of get_ routines below all provide one of the results of
the DQAP computation.

Each routine should be associated with a meta measurement.
The meta index should point to whatever measurement calls create_dqap
"""

@MEASUREMENT
def get_mean(val):
    return float(mean)


@MEASUREMENT
def get_stdev(val):
    return float(stdev)


@MEASUREMENT
def get_dqap(val):
    return float(dqap)


@MEASUREMENT
def get_num_dqap_samples(val):
    return float(num_dqap_samples)


@MEASUREMENT
def get_dqap_quality(val):
    return float(dqap_quality)
