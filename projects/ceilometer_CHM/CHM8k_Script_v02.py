from sl3 import *
from serial import Serial
import utime

### initiate variables for hourly values and hourly means
aero1_1hr = []
aero2_1hr = []
out_aero1_nn = []
out_aero2_mn = []
count = 0

### routing to set CHM8k to polling mode ###
@TASK 
def chm8k_set_polling():
    with Serial("RS485",9600) as portID:
        portID.timeout=0.5
        portID.reset_input_buffer()
        portID.write("set 16:TransferMode=0" + chr(10) + chr(13))
        print("polling mode enabled")
        portID.close()  

### routine to set CHM8k to automatic transfer mode ###
@TASK 
def chm8k_set_automatic():
    with Serial("RS485",9600) as portID:
        portID.timeout=0.5
        portID.reset_input_buffer()
        portID.write("set 16:TransferMode=6" + chr(10) + chr(13))
        print("automatic tranfer mode enabled")
        portID.close()

### polling routine for the CHM8k ###
@TASK 
def chm8k_polling():
    ### define variables with global access
    global aero1
    global aero2
    global cloud1
    global aero1_1hr
    global aero2_1hr
    global out_aero1_mn
    global out_aero2_mn
    global count
    
    ### serial port communication routine ###
    with Serial("RS485",9600) as portID:
        
        portID.timeout=0.5              # timeout for connecting with port
        portID.loopback = True          # return commands if needed
        portID.rs485 = True             # enable RS-485 comm mode on this port

        portID.reset_output_buffer()    # cleaning the output buffs
        portID.write('get 16:L' + chr(13) + chr(10))# send polling command to CHM8k
        portID.flush()                  # wait for all bytes to be send
        utime.sleep(0.005)              # obligatory gap between send and receive
        portID.reset_input_buffer()     # cleaning the input buffs for fresh data
        line = portID.readall()         # reading all available data in the port buffs
        print(line)                     # return the received data string to the user
    
    ### reading data from serial string ###
    aero1 = str(line).split(";")[40]    # split string at ";" and select "aerosol layer 1"
    aero2 = str(line).split(";")[41]    # split string at ";" and select "aerosol layer 2"
    cloud1 = str(line).split(";")[6]    # split string at ";" and select "cloud layer 1"
    
    timesum = str(line).split(";")[4]
    HH = float(str(timesum).split(":")[0])
    MM = float(str(timesum).split(":")[1])
    SS = float(str(timesum).split(":")[2])

    utime.sleep(0.05)
    count = count + 1
    
    ### handling missing data and filling hourly data vector ###
    if aero1 == "NODET":
        aero1 = float("nan")
    elif aero1 == "-----":
        aero1 = -2
    else:
        aero1 = float(aero1)
        aero1_1hr.append(aero1)

    if aero2 == "NODET":
        aero2 = float("nan")
    elif aero2 == "-----":
        aero2 = -2
    else:
        aero2 = float(aero2)
        aero2_1hr.append(aero2)

    if cloud1 == "NODET":
        cloud1 = float("nan")
    elif cloud1 == "-----":
        cloud1 = float("nan")
    else:
        cloud1 = float(cloud1)

    
    ### once per hour: calc the mean values from each hourly data vector ###
    if count == 12:
        ### aerosol layer 1 ###
        if len(aero1_1hr) == 0:
            out_aero1_mn = float("nan")
        else:
            out_aero1_mn = sum(aero1_1hr)/len(aero1_1hr)
        aero1_1hr = []      # reset vector for hourly data
        
        ### aerosol layer 2 ###
        if len(aero2_1hr) == 0:
            out_aero2_mn = float("nan")
        else:
            out_aero2_mn = sum(aero2_1hr)/len(aero2_1hr)
        aero2_1hr = []    # reset vector for hourly data

        count = 0
    
    # print(aero1)
    # print(aero2)
    # print(cloud1)
    # print(aero1_1hr)


### measurement functions and return arguments ###

@MEASUREMENT
def chm8k_read_aero1(arg):
    chm8k_polling()
    return(aero1)

@MEASUREMENT
def chm8k_read_aero2(arg):
    utime.sleep(0.2)
    return(aero2)

@MEASUREMENT
def chm8k_read_cloud1(arg):
    utime.sleep(0.3)
    return(cloud1)

@MEASUREMENT
def chm8k_aero1_mn(arg):
    utime.sleep(0.4)
    return(out_aero1_mn)

@MEASUREMENT
def chm8k_aero2_mn(arg):
    utime.sleep(0.5)
    return(out_aero2_mn)