# Example:  demonstrates formatting a message in DGA format

from sl3 import *


class SetupError(Exception):
    pass


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
    if more_info()[1] == True:
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

    dga_form += " "

    return dga_form
