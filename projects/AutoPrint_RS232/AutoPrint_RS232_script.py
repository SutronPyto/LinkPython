# Formats and outputs measurement data on the RS232 port

from sl3 import *
import utime
import serial



def format_number_right_digits(value, right_digits):
    """
    Formats the provided value with the correct number of right digits
    E.g. if value is 1.258999 and right_digits is 3, it returns "1.259"

    :param value: the number to format
    :type value: float
    :param right_digits: print how many digits after the decimal point?
    :type right_digits: int
    :return: the formatted value
    :rtype: str
    """
    result = ('{0:.{1}f}'.format(value, right_digits))
    return result


def format_meas(time, include_batt):
    """
    Formats all active measurements into a string that looks like
    “04/22/21,13:30:00,13.94,1.78,2.89”
    where we have date MM/DD/YY,time HH:MM:SS,battery voltage,measurement M1,measurement M2

    :param include_batt: should the data include the current battery voltage?
    :type include_batt: bool
    :return: formatted measurement data
    :rtype: str
    """
    out = ascii_time(time)

    # include the battery voltage?
    if include_batt:
        out += ","
        out += format_number_right_digits(batt(), 2)

    # format all the  measurement readings
    for meas_index in range(1, 10):

        # is this measurement active?
        if "ON" in setup_read("M{} Active".format(meas_index)).upper():

            # get the measurement reading
            reading = measure(meas_index)

            # format the value
            out += ","
            out += format_number_right_digits(reading.value, reading.right_digits)

    # add the delimiter at the end
    out += "\n"
    return out

    
@TASK
def output_data():
    """
    Outputs measurement data on the RS232 port
    """
    message = format_meas(time_scheduled(), True)
    with serial.Serial("RS232", 19200) as output:
        output.write(message)
        output.flush()  # needed to make sure all the data is sent before closing the port.

    # for diagnostics in script status:
    print(message)



