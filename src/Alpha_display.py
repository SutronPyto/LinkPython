# Example:  demonstrates writting data to an Alpha Display module over RS232

"""
This script will display the station name, measurement label, and value on an Alpha Display connected to the RS232 port.
To do this, setup the alpha_display task to run at whatever frequency you want the display to refresh. (5 or 10 sec is good)
Assign the add_to_display function to each measurement you want to display. (this is done in the measurement tab)
The alpha_display function will automatically update the list of measurements to display when you enable or display
any measurement in the setup and it will also scale the sleep period between each measurement to fit the display
refresh interval.

These functions will configure and display data on an Alpha display. The displays can do autobauding
but you need to send 5 NUL characters before <SOH>. Configuring SL3 for RS232 and 9600 baud rate works too
without sending NUL characters.
example command string to display "SL3 TEST" on all display addresses: <SOH>"Z00"<STX>"AASL3 TEST"<EOT>

    ==============   =========================================================================
    Code             Description
    ==============   =========================================================================
    SOH              start of header character
    Z                Type code, "Z" means transmission is directed to all sign types
    00               Sign code, "00" means all signs on network should listen to transmission
    STX              Start of text character
    A                Command code, "A" means write text file
    A                File label, "A" is file label of the text file
    SL3 Test         The actual string to display
    EOT              End of transmission character
    ==============   =========================================================================
"""
from sl3 import *

#common constants used in command strings
NUL = chr(0)
SOH = chr(1)
STX = chr(2)
ETX = chr(3)
EOT = chr(4)
LF = chr(10)
CR = chr(13)
DLE = chr(16)
ESC = chr(27)
TOP_L = chr(34)
BOT_L = chr(38)
FILL = chr(48)
DC2 = chr(18)

#dictionary gets populated when measurement function is assigned to a measurement and is triggered. The key is the measurement label
#and the value is the string to send to the display.
measDict = {}
active_meas_count = 0

def frame_wrapper(str_data):
    "Adds required control commands to data being displayed."
    # File label A is automatically setup when display is powered. It can be used immediately. Other labels will require memory
    # configuration before they can be written to.
    # SOH  - start of header character
    # Z    - Type code, "Z" means transmission is directed to all sign types
    # 00   - Sign code, "00" means all signs on network should listen to transmission
    # STX  - Start of text character
    # A    - Command code, "A" means write text file
    # A    - File label, "A" is file label of the text file
    # ESC  - Indicates special command code is next
    # b    - special command code indicating hold data. (other choices are flashing, twinkling, ect.)
    # str_data - Variable containing actual string to display
    # EOT  - End of transmission character
    return SOH + "Z00" + STX + "AA" + ESC + " b" + str_data + EOT

@TASK
def alpha_display():
    """"This function should be setup as a script to run at the desired display refresh schedule. It will simply output data
    on the RS232 port to an Alpha display. The data is pulled form measDict dictionary which is populated by the
    add_to_display measurement function. If any measurement is enabled or disabled, the dictionary is cleared and only
    active measurements will repopulate it at the next measurement interval."""

    import serial
    import utime

    global setup_alpha_display, active_meas_count, measDict

    current_active_meas_count = len(setup_read("last").strip().split("\r\n"))

    #delete all entries in measurement dictionary when the number of active measurements changes. Active measurements
    #will repopulate the dictionary when they are triggered.
    if current_active_meas_count != active_meas_count:
        measDict = {} #clear dictionary if number of measurements change
        active_meas_count = current_active_meas_count

    if is_being_tested():
        s_interval = 5
    else:
        s_interval = int(command_line("!s{} scheduled interval".format(index()), 100).strip().split(":")[2])

    #skip updating display if measurement dictionary got reset due to a setup change.
    if len(measDict) > 0:
        with serial.Serial("RS232",9600) as display:
            for keys in measDict:
                display.write(frame_wrapper(measDict[keys]))
                utime.sleep(s_interval/len(measDict))
            display.flush()

@MEASUREMENT
def add_to_display(inval):
    """
    Assign this function to a measurement and it will add that measurement to a dictionary from which the display
    task will pull and display data from. This can be assigned to multiple measurements.
    :param inval: measurement value
    :return: unmodified measurement value
    :rtype: float
    """

    stn_name = command_line("!station name", 100).strip()

    #this fuction can be assigned to multiple measurements so global lock is used to prevent all measurements from
    #updating the dictionary at the same time.
    with GLOBAL_LOCK:
        if is_being_tested():
            temp = measure(1, READING_LAST)
        else:
            temp = measure(index(), READING_LAST)

        temp_string = stn_name + chr(13) + str(temp.label) + " = " + "{:.2f}".format(inval) + " " + str(temp.units)

        #add measurement label to dictionary and/or update display string associated with dictionary key.
        measDict[temp.label] = temp_string

    return inval