OTT Hydromet Sat/XLink readme for connecting to a High Sierra IceSight sensor 

Files IceSight.py (script) and IceSight_setup.txt (setup) are used to have Sat/XLink collect data from the IceSight sensor.

Requirements
IceSight connected to Sat/XLink via RS-232
IceSight powered on all the time
IceSight at defaults

Once recording is turned on, Satlink will continuously capture data on the RS232 port.
When measurements are made, data from the last capture will be used to provide results.
If there is no data from the sensor in 20 seconds, measurement results will become -9999.

Script Task S2 may be used to check on the status of the script.  Run S2 and it will provide the last line of data collected from the sensor.   

Please see the setup file in LinkComm to see what sensor parameters are being collected by Sat/XLink.  To add more, modify the Python file by adding one function for each parameter.  Search script for @MEAS - those are the functions connected to measurements.

