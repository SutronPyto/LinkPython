# Example:  Computes a median value from many samples
"""
A Sat/XLink setup is associated with this module:
`median_setup.txt <median_setup.txt>`_

The setup requires that one measurement be setup to collect samples from the sensor (e.g. every 5 seconds).  It gets connected to the one_sample script function.  It does not get logged.  Instead, the samples get stored in temporary memory.
A second measurement is setup to compute the median.  It is a manual entry measurement (it does not sample the sensor).  It should happen less frequently than the first measurement (e.g. every hour).  It is logged and may be transmitted.
"""

from sl3 import *
import utime

sample_list = []  # samples are stored here


def compute_median(numbers_list):
    """ computes median on numbers in  list"""
    numbers_list = sorted(numbers_list)
    n = len(numbers_list)
    i = n // 2
    if n % 2 == 1:
        return numbers_list[i]
    else:
        return sum(numbers_list[i-1:i+1])/2
    

@MEASUREMENT
def one_sample(value):
    """ adds a sample to the list for later computation """
    global sample_list

    """ wait a touch to let the median computation complete first
    otherwise, if a new sample is collected at the same time
    as the median is computed, the new sample would end up in the
    computation for the old median """
    utime.sleep(0.1)

    lock()  # protect data

    sample_list.append(value)  # add value to list

    unlock()  # MUST unlock after locking.  otherwise, no other script could ever run

    if sutron_link:
        print("sample: ", value, ", ", ascii_time(utime.localtime()))
    meas_do_not_log()
    return value


@MEASUREMENT
def median_meas(ignored):
    """ computes the median over the collected samples """

    global sample_list

    lock()  # protect data

    median_value = compute_median(sample_list)  # compute the median

    if sutron_link:
        print("sample count: ", len(sample_list), " median: ", median_value, ", ", ascii_time(utime.localtime()))

    sample_list.clear()  # clear the list

    unlock()  # MUST unlock after locking.  otherwise, no other script could ever run

    return median_value


def test_median():
    """ test that the median is computed correctly"""

    """ 
    samples 1.0, 2.0, 4.0, 7.0
    median = 3.0
    """
    test_list = [1, 2, 4, 7]
    for i in test_list:
        one_sample(i)
    assert(3.0 == median_meas(0))

    """
    samples 13.0, 13.0, 13.0, 13.0, 14.0, 14.0, 16.0, 18.0, 21.0
    median = 14.0
    """
    test_list = [13.0, 13.0, 13.0, 13.0, 14.0, 14.0, 16.0, 18.0, 21.0]
    for i in test_list:
        one_sample(i)
    assert(14.0 == median_meas(0))

