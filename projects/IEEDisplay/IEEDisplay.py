""" Script displays sensor data on IEE RS232 display

Expects Sat/XLink have two measurements setup with these exact labels:
PL1
TL2
Uses units and number of right digits that are setup in the measurement

Setup a task to run shortly after both measurements have completed
Connect task to the routine iee_display

Outputs two lines such as
HEAD 1.234FT
TAIL 2.345FT
"""

from sl3 import *
import serial


@TASK
def iee_display():
    """Sends data to the EyeTV RS232 display"""

    with serial.Serial("RS232", 9600) as port:

        # get last head reading
        head_reading = measure('PL1', READING_LAST)
        if head_reading.quality == 'G':
            display_me = "HEAD {:.{}f}{}\r\n".format(head_reading.value, head_reading.right_digits, head_reading.units)
        else:
            display_me = "HEAD ERROR"
        print(display_me)  # for diagnostics via script status
        port.write(display_me)  # output to display

        # get last tail reading
        tail_reading = measure('TL2', READING_LAST)
        if tail_reading.quality == 'G':
            display_me = "TAIL {:.{}f}{}\r\n".format(tail_reading.value, tail_reading.right_digits, tail_reading.units)
        else:
            display_me = "TAIL ERROR"
        print(display_me)  # for diagnostics via script status
        port.write(display_me)  # output to display

        # make sure all the data is sent before closing the port
        port.flush()

