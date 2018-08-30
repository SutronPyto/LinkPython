# Example:  demonstrates reading the SonTek RS232 sensor

from sl3 import *
import utime
import serial

#global variables updated with each get_data() call
temperature = float(-999999.1)
pressure = float(-999999.1)
velocity_east = float(-999999.1)
update_in_progress = False
last_meas_time = 0

def sontek_com(command, sontek):

    sontek.reset_input_buffer()
    sontek.write(command + chr(13))
    buf = sontek.read(512)

    return buf

@TASK
def sontek_sync_time():
    """sync sontek time to sl3 time."""

    with serial.Serial("RS232", 9600) as sontek:
        sontek.send_break(.31) #wake up and bring ADP into command mode to make setup changes. requires a minimum of 300ms.
        utime.sleep(2) #requires a minimum of 1.56 seconds after break
        sontek.timeout = 2
        sontek.inter_byte_timeout = .01

        sl3_time = utime.localtime()
        date_response = sontek_com("date {:04d}/{:02d}/{:02d}".format(sl3_time[0], sl3_time[1], sl3_time[2]), sontek) #set sontek date
        time_response = sontek_com("time {:02d}:{:02d}:{:02d}".format(sl3_time[3], sl3_time[4], sl3_time[5]), sontek) #set sontek time
        start_response = sontek_com("start", sontek) #change to data acquisition mode

        time_response = str(time_response).strip().strip("b'").split("\\r\\n")
        #start_response = str(start_response).strip().strip("b'").split("\\r\\n")

        try:
            if time_response[0] != "OK" and time_response[2] != "OK":
                print("Date & time response is not OK. Date = {}, time = {}.".format(time_response[0], time_response[2]))
        except IndexError as e:
            print("Response is not as expect but likely ok if it is an indexerror. error type = {}".format(e))

@TASK
def get_data():
    """This routine is called by all measurements that need data from sontek. A single call populates values needed by
    measurements into global variables. Multiple calls to this routine within 5 seconds will only update the global
    variables once. This is to prevent opening and closing the port too rapidly which might impact the buffers and create
    bad data. A -999999.2 in log indicates sontek did not produce an expected response to command."""

    global temperature
    global pressure
    global velocity_east
    global last_meas_time
    global update_in_progress

    #timeout period between communication with sontek is set to 5 seconds. New requests for data will simply use data from the previous
    #request since all data is refreshed each time the port to sontek is opened.
    if (utime.time() - last_meas_time > 10):
        last_meas_time = utime.time()  # updating last measurement time
        update_in_progress = True
        with serial.Serial("RS232", 9600) as sontek:
            sontek.timeout = 2
            sontek.inter_byte_timeout = .01
            str_data = sontek_com("o", sontek) #get data in data acquisition mode

        try:
            temperature = float(str(str_data).split("\n")[0].split("\\n")[2].split()[3])*.01 #4th item on line 3 header
            pressure = float(str(str_data).split("\n")[0].split("\\n")[2].split()[4])  # 5th item on line 3 of header
            velocity_east = float(str(str_data).split("\n")[0].split("\\n")[4].split()[1])  #second item on line 5
        except IndexError as e:
            print(e)
            # setting each value out of range with a .2 to indicate what failed in log data.
            temperature = float(-999999.2)
            pressure = float(-999999.2)
            velocity_east = float(-999999.2)
        update_in_progress = False
    else:
        print("Meas request less than 5 seconds since last. No new data.")
    if update_in_progress == True:
        utime.sleep(2.5) #Allowing variables to be updated before proceeding if multiple measurements activate at once.


@MEASUREMENT
def sontek_temperature(arg):
    get_data()
    return(temperature)


@MEASUREMENT
def sontek_pressure(arg):
    utime.sleep(.02) #prevent all 3 measurements from triggering at once if they are scheduled at the same time. Allow temp to complete before getting data.
    get_data()
    return(pressure)

@MEASUREMENT
def sontek_Velocity_east_depth_1(arg):
    utime.sleep(.04) #prevent all 3 measurements from triggering at once if they are scheduled at the same time. Allow temp to complete before getting data.
    get_data()
    return(velocity_east)