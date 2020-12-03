""" Script displays sensor data on IEE RS232 display

Various options are provided via the @TASK functions below
Please check each @TASK function

Setup a task to run shortly after measurements have completed
Connect task to the routine iee_display

Use Script Status in LinkComm to view recent output
"""

from sl3 import *
import serial


def clear_display(port, lines):
    """
    :param port: serial port to use
    :type port: class Serial
    :param lines: how many lines to display
    :type lines: int
    :return: None
    """
    """ Clears display by writing blank lines to the port """
    for i in range(lines):
        port.write("\r\n")


def iee_display_one_meas(port, meas_to_display, heading, display_meas_time):
    """ Writes provided measurement to one line of the display
        Uses units and number of right digits that are setup in the measurement
        Optionally writes time of measurement on line two
    :param port: serial port to use
    :type port: Serial
    :param meas_to_display: which measurement to display
    :type meas_to_display: either measurement index (e.g. 1), or meas label (e.g. "PL1")
    :param heading: what text to show before the measurement
    :type heading: str
    :param display_meas_time: should the time of the measurement be displayed on the second line?
    :type display_meas_time: Bool
    :return: None
    """

    # format the measurement into one line
    if meas_to_display.quality == 'G':  # good quality reading format the value
        display_me = "{} {:.{}f}{}\r\n".format(heading,
                                               meas_to_display.value,
                                               meas_to_display.right_digits,
                                               meas_to_display.units)
    else:  # bad quality.  show error
        display_me = "{} ERROR\r\n".format(heading)
    print(display_me)  # for diagnostics via script status
    port.write(display_me)  # output to display

    # if caller asked, output time on a new line
    if display_meas_time:
        display_me = ascii_time_hms(meas_to_display.time)
        display_me += "\r\n"  # add new line
        print(display_me)  # for diagnostics via script status
        port.write(display_me)  # output to display


@TASK
def iee_display_two_line():
    """Sends data to the RS232 display
    Expects Sat/XLink have two measurements setup with these exact labels:
    PL1
    TL2
    Data is sent to a two line display and looks like so

    HEAD 1.234FT
    TAIL 2.345FT
    """

    with serial.Serial("RS232", 9600) as port:

        # start by clearing display:
        clear_display(port, 2)  # 2 means 2 line display

        # get last head reading using the label PL1:
        head_reading = measure('PL1', READING_LAST)

        # display the reading
        iee_display_one_meas(port,
                             head_reading,  # this is the measurement to show
                             "HEAD",  # print this before meas value
                             False)  # do not display meas time

        # get last tail reading
        tail_reading = measure('TL2', READING_LAST)

        # display the reading
        iee_display_one_meas(port, tail_reading, "TAIL", False)

        # make sure all the data is sent before closing the port
        port.flush()


@TASK
def iee_display_four_line_two_meas():
    """Sends data to the RS232 display
    Uses a 4 line display
    Uses measurements M1 and M2 (labels are not relevant)
    Prints measurement label, value, units on line one
    Prints measurement timestamp on line two
    Output depends on setup, but if M1 were labeled HEAD and M2 were TAIL:
    HEAD 1.234FT
    12:15:00
    TAIL 2.345FT
    12:15:00
    """

    with serial.Serial("RS232", 9600) as port:

        # start by clearing display:
        clear_display(port, 4)  # 4 means 4 line display

        # get last reading for measurement index M1
        reading = measure(1, READING_LAST)

        # display the reading
        iee_display_one_meas(port,
                             reading,
                             reading.label,  # show meas label before value
                             True)  # True means display meas time

        # get last reading for measurement index M2
        reading = measure(2, READING_LAST)

        # display the reading
        iee_display_one_meas(port, reading, reading.label,True)

        # make sure all the data is sent before closing the port
        port.flush()


@TASK
def iee_display_four_meas():
    """Sends data to the RS232 display
    M1, M2, M3 and M4 are displayed on a 4 line display
    Output depends on setup, but here is an example:
    BV 12.5V
    AT 21.9C
    RAIN 0.02in
    HG 2.345ft
    """

    with serial.Serial("RS232", 9600) as port:

        # start by clearing display:
        clear_display(port, 4)  # 4 means 4 line display

        # loop for meas M1 to M4:
        for meas_index in range(1, 5):  # 1 through 4
            # get last reading
            reading = measure(meas_index, READING_LAST)

            # display the reading
            iee_display_one_meas(port, reading, reading.label, False)

        # make sure all the data is sent before closing the port
        port.flush()
