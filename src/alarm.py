# Example:  Increase the measurement and transmission rates when the system is in alarm
"""
Normal mode (not in alarm):
    Measure and log sensor at a normal rate (5 min)
    Transmit at a normal rate of 10 min
If system goes into alarm (based on standard setup), go into fast mode:
    measure and log sensor at a fast rate (30 sec)
    transmit at a fast rate of 1 min

Setup details::

!M1 MEAS INTERVAL=00:05:00
!M1 ALARM 1 THRESHOLD=10.000000
!M1 ALARM 1 TYPE=High
!M1 TX DATA CONTENT3=All Since Last Tx
!TX3 KIND=Scheduled
!TX3 MODE=Internet Only
!TX3 RADIO TYPE=Cell
!TX3 SCHEDULED INTERVAL=00:15:00
!S1 SCRIPT FUNCTION=alarm_in_a
!S1 TRIGGER=Alarm In Only
!S2 SCRIPT FUNCTION=alarm_out_a
!S2 TRIGGER=Alarm Out Only
"""
from sl3 import *


@TASK
def alarm_in_a():
    """script task should be setup when system goes into alarms to increase meas and tx rate"""
    setup_write("!M1 meas interval", "00:00:15")
    setup_write("!TX3 scheduled interval", "00:02:00")


@TASK
def alarm_out_a():
    """script task should be setup when system goes out of alarms to slow meas and tx rate"""
    setup_write("!M1 meas interval", "00:05:00")
    setup_write("!TX3 scheduled interval", "00:15:00")
