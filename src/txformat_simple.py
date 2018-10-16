# Example:  demonstrates some simple TX format scripts

from sl3 import *


@TXFORMAT
def append_info(standard):
    """appends information to tx"""
    return standard + " Little Creek A21938"


"""this id is unique to each station"""
unique_id = "A17_BS_128"


@TXFORMAT
def prefix_id_1(standard):
    """prefixes station id"""
    global unique_id
    return unique_id + " " + standard


@TXFORMAT
def prefix_id_2(standard):
    """prefixes station name"""
    station_name = command_line("!STATION NAME\r", 128).strip()
    return station_name + " " + standard


@TXFORMAT
def destroy(standard):
    """destroys standard format"""
    return "kittens ate your data"


def format_number_right_digits(value, right_digits):
    """
    Formats the provided value with the correct number of right digits
    E.g. if value is 1.258999 and right_digits is 3, it returns "1.259"

    :param value: the number to format
    :type value: float
    :param right_digits: print how many digits after the decimal point?
    :type right_digits: int
    :return: the formatted value
    :rtype: str
    """
    result = ('{0:.{1}f}'.format(value, right_digits))
    return result


def log_read_meas(meas_index_or_label, number_readings):
    """
    Reads the log looking for the most recent readings of the specified measurement.

    :param meas_index_or_label: either the index or the label of the meas.   1 or 'Sense1'
    :type meas_index_or_label: int or string
    :param number_readings: how many readings to format
    :type number_readings: int
    :return: readings from the log
    :rtype: log
    """

    # get the meas label so we can search the log for it
    if isinstance(meas_index_or_label, int):
        meas_label = meas_find_label(meas_index_or_label)
    else:
        meas_label = meas_index_or_label

    # read the log looking for the most recent readings
    log_data = Log(match=meas_label, count=number_readings, pos=LOG_NEWEST)

    return log_data


@TXFORMAT
def tx_format_a1(standard):
    """
    Implements the transmission format A1.  Data looks like so:
    Format A1: 10/16/2018,07:28:40
    BATT: 12.54, 12.98
    TEMP: missing
    MINO: missing
    end.

    The transmission starts with a fixed header and includes date and time.
    Two most recent readings from every active measurement are formatted.
    Each measurements tarts with the label.
    If readings are missing, it is noted.
    There is a footer indicating end of message.

    :param standard: this parameter is ignored
    :type standard: str
    :return: transmission data
    :rtype: str
    """

    # format the transmission header
    out = "Format A1: "

    # add the time and date
    out += ascii_time(time_scheduled())
    out += "\n"  # delimiter after header

    # how many readings of each measurement should we format?
    number_of_readings = 2

    # hos many right digits should format each measurement with?
    right_digits = 2

    # count active measurements
    meas_active = 0

    # format all the  measurement readings
    for meas_index in range(1, 33):

        # is this measurement active?
        if "ON" in setup_read("M{} Active".format(meas_index)).upper():

            meas_active += 1

            # format the header
            out += "{}: ".format(meas_find_label(meas_index))

            # count the readings we format to help with delimiters
            #   and missing data
            count_em = 0

            # read the log looking the measurement
            loggy = log_read_meas(meas_index, number_of_readings)
            for each in loggy:
                # if this is NOT the first value we format, add a delimiter
                if count_em >= 1:
                    out += ", "

                # format the value
                out += format_number_right_digits(each.value, right_digits)
                count_em += 1

            # if we found no readings in the log, add the missing indicator
            if not count_em:
                out += "missing"

            # add the delimiter after each measurement
            out += "\n"

    # if there are no active measurements, say so
    if meas_active == 0:
        out += "no active measurements\n"

    # add the footer
    out += "end."

    return out
