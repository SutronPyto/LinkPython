# Example:  Computes a moving sum value from previous samles
"""
A Sat/XLink setup is associated with this module:
`moving_sum_setup.txt <moving_sum_setup.txt>`_

One measurement is setup to sample the sensor every minute
A second measurement will compute the moving sum over the last 60 sensor samples every minute

FOr example, at 12:15:00, the moving sum will be computed on samples from 11:15 to 12:15.
At 12:16:00, it will be computed on data from 11:16 to 12:16, etc.
"""

from sl3 import *
import utime

""" Please change the value below to indicate how many samples should be summed up"""
sample_count = 60

sample_list = []  # samples are stored here


@MEASUREMENT
def moving_sum(sample):
    """ adds current sample to list and computes a moving sum over past samples """
    global sample_list, sample_count

    sample_list.append(sample)   # add sample

    if len(sample_list) > sample_count:  # list full.  remove oldest item
        del sample_list[0]

    return sum(sample_list)
