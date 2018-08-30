# Example:  demonstrates some simple custom measurements

from sl3 import *


@MEASUREMENT
def twelve_more(inval):
    """returns 12+input"""
    return 12 + inval


@MEASUREMENT
def amp_temp(inval):
    """measures amp temperature"""
    return internal_sensor(2)


@MEASUREMENT
def temp_compensation(inval):
    """compensates the value based on temperature"""
    temp = internal_sensor(1)

    result = inval
    if (temp < 25):
        result += 1.2
    elif (temp > 35):
        result -= 0.9

    return result


@MEASUREMENT
def dew_point(inval):
    """
    Computes dew point based on relative humidity and air temperature.
    It is assumed that two other measurements have been setup, one called AT and another called RH.
    This script should be associated with a third measurement that is setup as a Manual Entry.
    Manual Entry is used because this measurement is based on the inputs of two other sensors rather than the
    input associated with this measurement.

    :param inval: this value is ignored
    :return: dew point
    :rtype: float
    """
    from math import log10

    # retrieve relative humidity from another measurement which must be labeled RH
    rh = measure("RH").value

    # retrieve temperature from meas labeled AT
    at = measure("AT").value

    # compute dew point
    dp = 0.057906 * (log10(rh / 100) / 1.1805) + (at / (at + 238.3))
    dp = dp * 238.3 / (1 - dp)  # Formula for Dew point temperature

    return dp
