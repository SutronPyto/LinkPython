""" Script displays stage data on EyeTv RS232 display
Counts on a measurement labeled HG which provides the stage reading
Counts on several tasks
* one scheduled every 10 seconds for eye_tv_display_stage
* another triggered at bootup for eye_tv_inactive
* yet another triggered at when recording is stopped also for eye_tv_inactive
A null modem is needed to connect Sat/XLink to the display via RS232

When powered on, and when station is stopped,
display will say "INACTIVE"

If recording is on, system will update display every 10 seconds
with a scrolling message "STAGE = x.xx"

If there are no stage readings (yet), or if there is an error reading stage,
the display will say "NO STAGE"

If the display does not update every 10 seconds, there is a problem
"""

from sl3 import *
import serial


def eye_drive(port, display_data, act_e=1, wait_100ms=0, repeat=0, speed=30, pos_x=0, pos_y=0):
    """
    Drives the EyeTV display with provided data
    
    :param port: RS232 port which to use, should be open already 
    :type port: Serial
    :param display_data: data to display 
    :type display_data: str
    :param act_e: active effect
    :type act_e: int
    :param wait_100ms: if not 0, wait instruction is issued to display
    :type wait_100ms: int, units are 100s of ms
    :param repeat: if not zero, issues repeat command to display
    :type repeat: int, 255 means repeat forever, otherwise, repeat said number of times
    :param speed: controls scroll speed, 30ms is default, lower number is faster
    :type speed: int
    :param pos_x: horizontal position
    :type pos_x: int
    :param pos_y: vertical position
    :type pos_y: int
    :return: None
    """

    port.write('[TMODE]\r')  # start serial mode
    utime.sleep(0.5)  # wait for display

    # this would set the brightness to 5%
    port.write('[BRIGHT5]\r')  # normal brightness is too much for office

    # start comms w/ display
    port.write('[COMON]\r')

    # repeat?
    if repeat:
        repeat_str = '[REPEAT{}]\r'.format(repeat)
        port.write(repeat_str)

    # speed?
    if speed:
        speed_str = '[SPEED{}]\r'.format(speed)
        port.write(speed_str)

    # write position info
    pos_x = 0  # X coordinate where to write the data
    pos_y = 0  # Y coordinate where to write the data
    pos_str = '[PX{} PY{}]'.format(pos_x, pos_y)  # position info
    port.write(pos_str)

    # write actual data
    port.write(display_data)
    
    # effect
    act_str = '[ACT{}]\r'.format(act_e)
    port.write(act_str)

    # wait if needed
    if wait_100ms:
        wait_str = '[WAIT{}]\r'.format(wait_100ms)
        port.write(wait_str)

    # end comms w/ display
    port.write('[COMOFF]\r')


@TASK
def eye_tv_inactive():
    """Issue reset command to EyeTV RS232 display
    and display a message indicating station is inactive"""
    with serial.Serial("RS232", 115200) as port:

        port.write('[TMODE]\r')  # start serial mode
        utime.sleep(0.5)  # wait for display

        port.write('[TRESET]')  # reset display to defaults
        utime.sleep(5)  # wait for reset

        # display static message
        eye_drive(port, "INACTIVE", act_e=0)

        port.flush()  # needed to make sure all the data is sent before closing the port.


@TASK
def eye_tv_display_stage():
    """Sends data to the EyeTV RS232 display"""

    with serial.Serial("RS232", 115200) as port:

        # get last stage reading
        stage_reading = measure('HG', READING_LAST)
        if stage_reading.quality == 'G':
            display_me = "     {}={:.{}f}".format("STAGE", stage_reading.value, stage_reading.right_digits)
            # the preceeding spaces make it easy to read when scrolling
        else:
            display_me = "     No STAGE"

        # paint the display
        eye_drive(port, display_me, act_e=1, speed=50)
        # act_e 0 is static, 1 is scroll then wait, 8 is scroll off screen

        # make sure all the data is sent before closing the port
        port.flush()

        # for diagnostics via script status
        print(display_me)
        
