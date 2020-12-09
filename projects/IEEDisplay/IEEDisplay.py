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


def iee_display_time(port, time_to_show):
    """
    Displays provided time on the display
    :param port: serial port to use
    :type port: Serial
    :param time_to_show: time is represented in seconds since 1970 as returned by utime.time()
    :return: None
    """
    display_me = ascii_time_hms(time_to_show)
    display_me += "\r\n"  # add new line
    print(display_me)  # for diagnostics via script status
    port.write(display_me)  # output to display


def iee_display_one_meas(port, meas_to_display, heading):
    """ Writes provided measurement to one line of the display
        Uses units and number of right digits that are setup in the measurement
        Optionally writes time of measurement on line two
    :param port: serial port to use
    :type port: Serial
    :param meas_to_display: which measurement to display
    :type meas_to_display: either measurement index (e.g. 1), or meas label (e.g. "PL1")
    :param heading: what text to show before the measurement
    :type heading: str
    :return: None
    """

    # format the measurement into one line
    if meas_to_display.quality == 'G':  # good quality reading format the value
        display_me = "{} {:.{}f}{}\r\n".format(heading,
                                               meas_to_display.value,
                                               meas_to_display.right_digits,
                                               meas_to_display.units)
    else:  # bad quality.  show we do not have a reading
        display_me = "NA\r\n"
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
                             "HEAD");

        # get last tail reading
        tail_reading = measure('TL2', READING_LAST)

        # display the reading
        iee_display_one_meas(port, tail_reading, "TAIL")

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
            iee_display_one_meas(port, reading, reading.label)

        # make sure all the data is sent before closing the port
        port.flush()


@TASK
def iee_display_time_3_meas():
    """Sends data to the RS232 display
    Shows time on line one,
    M1, M2, M3 on the following lines
    Output depends on setup, but here is an example:
    12:15:00
    BV 12.5V
    AT 21.9C
    RAIN 0.02in
    """

    with serial.Serial("RS232", 9600) as port:

        # start by clearing display:
        clear_display(port, 4)  # 4 means 4 line display

        # get M1
        reading = measure(1, READING_LAST)

        # show time of M1 on line 1
        iee_display_time(port, reading.time)

        # show M1
        iee_display_one_meas(port, reading, reading.label)

        # get and show M2
        reading = measure(2, READING_LAST)
        iee_display_one_meas(port, reading, reading.label)

        # get and show M3
        reading = measure(3, READING_LAST)
        iee_display_one_meas(port, reading, reading.label)

        # make sure all the data is sent before closing the port
        port.flush()


@TASK
def iee_display_vorne_2():
    """Sends data to the RS232 display
    M1 and M2 are displayed on one line
    HEAD 1.234FT TAIL 2.345FT
    """

    with serial.Serial("RS232", 9600) as port:

        # get M1
        reading = measure(1, READING_LAST)

        # format the measurement into one line
        if reading.quality == 'G':  # good quality reading format the value
            display_m1 = "{} {:.{}f}{}".format(reading.label,
                                               reading.value,
                                               reading.right_digits,
                                               reading.units)
        else:  # bad quality.  show we do not have a reading
            display_m1 = "NA"

        # get M2
        reading = measure(2, READING_LAST)

        # format the measurement into one line
        if reading.quality == 'G':  # good quality reading format the value
            display_m2 = "{} {:.{}f}{}".format(reading.label,
                                               reading.value,
                                               reading.right_digits,
                                               reading.units)
        else:  # bad quality.  show we do not have a reading
            display_m2 = "NA"

        display_me = display_m1 + " " + display_m2 + "\r\n"

        print(display_me)  # for diagnostics via script status
        port.write(display_me)  # output to display

        # make sure all the data is sent before closing the port
        port.flush()


@TASK
def iee_display_vorne_2B():
    """Sends data to the RS232 display
    M3 and M4 are displayed on one line
    no units are shown
    HEAD 1.234 TAIL 2.345
    """

    with serial.Serial("RS232", 9600) as port:

        # get M3
        reading = measure(3, READING_LAST)

        # format the measurement into one line
        if reading.quality == 'G':  # good quality reading format the value
            display_1 = "{} {:.{}f}".format(reading.label,
                                            reading.value,
                                            reading.right_digits)
        else:  # bad quality.  show we do not have a reading
            display_1 = "NA"

        # get M4
        reading = measure(4, READING_LAST)

        # format the measurement into one line
        if reading.quality == 'G':  # good quality reading format the value
            display_2 = "{} {:.{}f}".format(reading.label,
                                            reading.value,
                                            reading.right_digits)
        else:  # bad quality.  show we do not have a reading
            display_2 = "NA"

        display_me = display_1 + " " + display_2 + "\r\n"

        print(display_me)  # for diagnostics via script status
        port.write(display_me)  # output to display

        # make sure all the data is sent before closing the port
        port.flush()
