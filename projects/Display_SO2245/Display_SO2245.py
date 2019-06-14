"""
Display controller
Outputs control characters for the display along with sensor data

Setup needs to have measurements with the labels DO and TEMP

Based on the 8210 basic program below:

10  OPEN "TERM:" nowait
15 If Err then goto 100
20  Control 1
30 Control 11,1200
35  a = DO
36  b = TEMP
37 Print 14$;48$;49$;3$;68$;79$;13$;15$;48$;49$;3$;
38 Sleep 2
40 Print 14$;48$;49$;3$;a!3!2;13$;15$;48$;49$;3$;
42 Sleep 15
45  '     ON|addr|addr|etx|data stuff|CR|off|addr|addr|etx
46 Print 14$;48$;49$;3$;84$;69$;77$;80$;13$;15$;48$;49$;3$;
47 Sleep 2
48 Print 14$;48$;49$;3$;b!3!2;13$;15$;48$;49$;3$;
50  Close
60 stop
100 open "DISPLAY:" nowait
105 Control 1
110 Print "TERM BUSY"; : Sleep 2
115 Control 2 : Close
120 goto 10


Based on the comments ON|addr|addr|etx|data stuff|CR|off|addr|addr|etx
    it appears we are writing to the same 'address' of the display
    First, we write the sensor name "DO", then we wait 2 sec
    Next, we write the actual sensor reading for "DO" (presumably dissolved oxygen), wait 15 sec
    After that, we write the sensor name "TEMP", and wait 2 sec
    Next, we write the actual sensor reading for temperature and wait 15 seconds

Python does not print literals in decimal like basic.  Python uses hex.
So, the literal values (e.g. '14$') were translated to hex ('\x0E').
Translation table:
ON
14$ = \x0E

addr
48$ = \x30
49$ = \x31

ETX
3$ = \x03

data stuff
68$ = 'D'
79$ = 'O'

84$ = 'T'
69$ = 'E'
77$ = 'M'
80$ = 'P'

CR
13$ = \x0D

OFF
$15 = \x0F`
"""

from sl3 import *
import serial
import utime

start_sequence =     '\x0E\x30\x31\x03'  # ON|addr|addr|etx
end_sequence   = '\x0D\x0F\x30\x31\x03'  # CR|off|addr|addr|etx


@TASK
def display_SO2245():

    # get the sensor readings
    do_reading = measure("DO").value
    temp_reading = measure("TEMP").value

    with serial.Serial("RS232", 1200) as output:
        # write 'DO'
        output.write(start_sequence)
        output.write('DO')
        output.write(end_sequence)
        utime.sleep(2)

        # write the value of the DO sensor
        output.write(start_sequence)
        output.write("{:.{}f}".format(do_reading, 2))  # 2 is the number of right digits
        output.write(end_sequence)
        utime.sleep(15)

        # write 'TEMP'
        output.write(start_sequence)
        output.write('TEMP')
        output.write(end_sequence)
        utime.sleep(2)

        # write the value of the TEMP sensor
        output.write(start_sequence)
        output.write("{:.{}f}".format(temp_reading, 2))  # 2 is the number of right digits
        output.write(end_sequence)
        utime.sleep(15)

        output.flush()  # needed to make sure all the data is sent before closing the port.
