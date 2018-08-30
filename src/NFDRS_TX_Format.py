# Example:  demonstrates SHEF reformatted to NRDRS transmission format using string comprehension
""""
This script takes in SHEF TX format and outputs NRDRS TX format. Measurements must be labeled in accordance with tx_sensor_order list.
If Tx format is not already in SHEF, script will change setting to SHEF and recalculate tx string::

SHEF format: ':RNIN 1 #0 12.34 :WSM 1 #0 -123 :WDD 1 #0 567 :ATF 1 #0 123 :FTF 1 #0 234 :RHP 1 #0 123 :BVV 1 #0 12.6 :FMP 1 #0 23.7 :WDDP 1 #0 123 :WSMP 1 #0 234 :SRW 1 #0 12345'

NRDRS output: '12.34\r\n-123\r\n567\r\n123\r\n234\r\n123\r\n12.6\r\n23.7\r\n123\r\n234\r\n12345\r\n'

(Note that '\r\n' are carriage returns and new lines which are not printed)
"""
from sl3 import *

def sl3_round(x):
    """ rounding is needed for SL3 since 'float' makes some values slightly smaller. example: 25 turns into 24.9999999 which becomes 24"""
    return x+sgn(x)*0.0000001

@TXFORMAT
def NRDRS_format(shef):
    """ Takes in SHEF TX format and outputs NRDRS TX format.

    :param shef: String containing SHEF formatted TX output.
    :return: String containing NRDRS formatted TX output.
    :rtype: str
    """

    tx_format_setting = setup_read('!tx{} format'.format(index())).strip()
    try:
        # Changing tx format to SHEF if it isn't already and reforming tx message
        if tx_format_setting != 'SHEF':
            setup_write("!tx{} format".format(index()),"SHEF")
            setup_write("!tx{} custom script format".format(index()),"off")
            print("tx format changed form {} to SHEF".format(tx_format_setting))
            shef = setup_read("!tx{} txform".format(index())).split('\r\n\r\n')[1]
            setup_write("!tx{} custom script format".format(index()), "on")
        else:
            print("tx format is {}.".format(tx_format_setting))
    except Exception as e:
        print(e)

    # User specified sensor name and TX order
    tx_sensor_order = ['RNIN', 'WSM', 'WDD', 'ATF', 'FTF', 'RHP', 'BVV', 'FMP', 'WDDP', 'WSMP', 'SRW']

    # User specified tx digits
    tx_sensor_digits = [2,0,0,0,0,0,1,1,0,0,0]

    tx_str = '' # Initializing new empty tx string
    shef_list = shef.split(":")

    # iterating through tx_sensor_order list and keeping track of element index with x to use with digits list.
    for x, sensor in enumerate(tx_sensor_order):
        try:
            # We want the first element of output list which starts with sensor label in shef_list.
            # The space appended to sensor label is to match full word rather than partial match such as 'WDD' and 'WDDP'.
            sensor_str = [s for s in shef_list if s.startswith(sensor+' ')][0]

            # Extract last value from individual sensor string and cast it as float
            sensor_str = float(sensor_str.split()[-1])

            # Append the rounded value to tx_str and limit the precision to digits specified in tx_sensor_digits list.
            tx_str += '{:.{digits}f}\r\n'.format(sl3_round(sensor_str),digits=tx_sensor_digits[x])
        except IndexError as e:
            print("sensor {} not found. Ignoring and moving on.".format(sensor))
        except Exception as e:
            print("Error: {}".format(e))
    print(" ".join(tx_str.split('\r\n')))
    return tx_str

# test string
print(NRDRS_format(':RNIN 1 #0 12.34 11.983 :WSM 1 #0 -123 :WDD 1 #0 567 :ATF 1 #0 123 :FTF 1 #0 234 :RHP 1 #0 123'
                   ':BVV 1 #0 12.6 :FMP 1 #0 23.7 :WDDP 1 #0 123 :WSMP 1 #0 234 :SRW 1 #0 12345.12'))
