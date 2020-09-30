# Example:  demonstrates formatting a message in DGA format

import re
from sl3 import *


class SetupError(Exception):
    pass


def cell_sig_str_bars():
    """
    Returns the cell modem signal strength in bars
    :return: signal strength in bars (0 to 4)
    :rtype: int
    """

    # assume there is no signal
    sig_str = 0

    status_cell = command_line("!STATUS CELL")
    # the reply to that command will have a line such as
    # Cell signal: 3/4 bars at 2019/11/08 14:40:10
    # we need the number of bars, which is 3 in the example above

    # split it into lines
    all_lines = status_cell.split("\r\n")

    # go through each line, looking for signal strength
    found = False
    for one_line in all_lines:
        if ("Cell signal:" in one_line):
            found = True
            break

    if found:
        try:
            # strip leading whitespace
            clean_line = one_line.lstrip()

            # split the string into tokens separated by space
            tokens = clean_line.split(' ')

            # get the token before the / (e.g. 3/4)
            sig_tok = tokens[2].split('/')

            sig_str = int(sig_tok[0])
        except ValueError:
            pass
        except IndexError:
            pass

    return sig_str


def bars_to_dbm(bars):
    """
    Converts cell modem signal strength from bars to dBm

    :param bars: sig str in bars, 0 to 4
    :type bars: int
    :return: sig str in dBm
    :rtype: int
"""
    rssi = 0
    if bars == 1:
        rssi = 5
    elif bars == 2:
        rssi = 13
    elif bars == 3:
        rssi = 21
    elif bars == 4:
        rssi = 28
    db = rssi*2 - 113
    return db


@TXFORMAT
def dga_format(txformat):
    """
    This script provides DGA formatting for transmissions
    It is required that the system be setup for CSV formatting

    Example incoming TXform in CSV on SL3:
            04/20/2017,19:55:00,PRECI,2.50,,G
            04/20/2017,19:55:00,TAIRE,2.50,,G
            04/20/2017,19:55:00,BATER,2.50,,G
    Expected TXform output from script:
        'SELFTIMED ON UNIT: DGATEST DATE: 04/20/2017 TIME: 19:55:00 PRECI 2.50 G OK  TAIRE 2.50 G OK  BATER 2.50 G OK  '

    :param txformat: CSV string
    :return: reformat to DGA format requirements.
    :rtype: str
    """

    # PC testing returns a False for scheduled reading and True when used on SL3 when scheduled.
    # This allows you to test code on PC and load it into SL3 without having to modify any code.
    if is_scheduled() == True:
        tx_format = command_line("!tx{} format".format(index()), 50).strip()
        if not ("CSV" in tx_format):
            raise SetupError("Wrong tx{} format setup. Change format to CSV.".format(index()))

    if is_being_tested():
        # if tested on sl3 and txformat does not have legitimate value passed in, set to typical value
        if not (txformat.strip().split("/")[0].isdigit()):
            txformat = "\r\n05/12/2017,15:18:00,Temp,26.00,,G\r\n05/12/2017,15:18:00,Batt,12.51,,G\r\n\r\n"

    meas_list = txformat.strip().split("\r\n")
    st_name = command_line("!station name", 100).strip()
    m_date, m_time = meas_list[0].split(",")[:2]
    dga_form = "SELFTIMED ON UNIT: {} DATE: {} TIME: {}".format(st_name, m_date, m_time)

    # Iterating through all measurements in tx buffer and appending meas name,
    # value, and quality to dga formatted tx buffer
    for measurement in meas_list:
        fields = measurement.split(",")
        m_name, m_val = fields[2], fields[3]

        if m_val == "MISSING":
            dga_form += " {} {} OK ".format(m_name, m_val)
        else:
            m_qual = fields[5]
            dga_form += " {} {} {} OK ".format(m_name, m_val, m_qual)

    # signal strength
    sig_str = bars_to_dbm(cell_sig_str_bars())
    # e.g. "SIGNAL 3 G OK "
    dga_form += " SIGNAL {} G OK ".format(sig_str)

    dga_form += " "

    return dga_form

