""" AML Oceanographic Smart X 'Simulator'
The unit running this script will output a serial data stream
that mimics the AML sensor.  Data looks like so
 22.502  20.561  0000.000

Setup is associated with this script.  It is expected that the setup
has three measurements used to create data for the output

 """
from sl3 import *
import serial

""" setup the serial port but do not open it"""
port = serial.Serial()
port_opened = False


def port_open():
    # configures and opens the serial port IF port_opened is False
    global port
    global port_opened

    lock()  # thread safe access
    if not port_opened:
        port.port = "RS232"
        port.baudrate = 9600
        port.parity = 'N'
        port.stopbits = 1
        port.rtscts = False
        port.dsrdtr = False
        port.xonxoff = False
        port.timeout = 2
        port.inter_byte_timeout = 0.2  # seconds to wait between bytes
        port.open()
        port_opened = True
    unlock()


@TASK
def port_close():
    # closes the serial port IF port_opened is True
    global port
    global port_opened

    lock()  # thread safe access

    if port_opened:
        port.flush()
        port.close()
        port_opened = False
    unlock()


def aml_format_3_meas():
    """
    Formats up the most recent reading of M1, M2, and M3
    Format is AMS sensor style e.g.
     22.212  20.557  0000.000

    leads with a space, delimits with 2 spaces, ends with \r

    :return: Formatted string
    :rtype: str
    """

    result = ""
    first = True

    for m in range(1, 3 + 1):
        r = measure(m, READING_LAST)
        if first:  # first active measurement found
            result = " "  # one space before first reading
            first = False
        else:
            result += "  "  # two spaces after each reading

        # format the value with the user set right digts
        result += "{:.{}f}".format(r.value, r.right_digits)

    result += "\r"
    return result


@TASK
def output_data_global():
    """Puts data from aml_format_3_meas """

    # we keep the port port_opened.  forever
    port_open()

    # output data on port
    data_out = aml_format_3_meas()
    port.write(data_out)

    # print for diagnostics
    print(data_out)
