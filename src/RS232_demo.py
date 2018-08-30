# Example:  demonstrates writing to the RS232 port

from sl3 import *
import serial


@TASK
def rs232_hello_world():
    """
    This is a very basic example showing how to open an RS232 port,
    output "Hello World", and close port.
    Configure Teraterm on the PC to the appropriate com port with the settings
    (9600, 8, none, 1, none), and connect to Satlink's RS232 to view the output.
    """
    with serial.Serial("RS232", 9600) as output:
        output.write("Hello World")
        output.flush()  # needed to make sure all the data is sent before closing the port.


@TASK
def rs232_last_meas():
    """
    This RS232 example shows how to output the last value of measurement M1 in CSV format.
    Example::

        08/05/2017,17:01:40,BATT,13.156,V,G
    """
    with serial.Serial("RS232", 9600) as output:
        output.write(str(measure(1, READING_LAST)) + "\r\n")
        output.flush()  # needed to make sure all the data is sent before closing the port.


def format_all_active_meas():
    """
    Formats up the most recent reading of every active measurement.
    Example output::

        BATT: 13.141
        TEMP: 29.250

    :return: A human readable string containing the label and value of each measurement
    :rtype: str
    """

    result = "No active meas found\r\n"
    first = True

    # loop through all the measurements, looking for active ones
    for m in range(1, 32 + 1):
        if "On" in setup_read("M{} Active".format(m)):
            # found an active measurement
            r = measure(m, READING_LAST)
            if first:  # first active measurement found
                result = "\r\n"
                first = False

            # format up the label and the value with the correct number of right digits
            result += "{}: {:.{}f}\r\n".format(r.label, r.value, r.right_digits)

    return result


@TASK
def display_all_active_meas():
    """Sends the last reading of every active measurement on the RS232 port"""

    with serial.Serial("RS232", 9600) as output:
        output.write(format_all_active_meas())
        output.flush()  # needed to make sure all the data is sent before closing the port.
