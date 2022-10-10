"""
Tx format script converts ASCII column format:
adds the measurement label before each value of ASCII column format
and changes spaces between measurements to semicolons

Original format:
100 100 100 100

Converted:
H1: 100; TW: 100; VB: 100; RG: 100

"""

from sl3 import *


def format_mod_column_label(column_format, label_list):
    """
    modifies ASCII column format as noted above

    :param column_format: ASCII column formatted data
    :type column_format: str
    :param label_list: measurement labels
    :type label_list: string list
    :return: modified format
    :rtype: str
    """

    lines = column_format.strip().split("\r\n")
    new_format = ""

    # split into lines
    for i in range(len(lines)):

        # split line into single readings
        readings = lines[i].strip().split(" ")
        for j in range(len(readings)):
            convert_one = "{}: {}".format(label_list[j], readings[j])
            if (j+1) == len(readings):  # last value
                convert_one = convert_one + "\r\n"
            else:
                convert_one = convert_one + "; "
            new_format = new_format + convert_one

    return new_format


@TXFORMAT
def format_mod_column(column_format):
    """see format_mod_column_time"""

    # loop through all the measurements, looking for active ones
    # add active meas label to list
    label_list = []
    for m in range(1, 32 + 1):
        if "On" in setup_read("M{} Active".format(m)):
            # found an active measurement
            label = setup_read("M{} Label".format(m))
            label_list.append(label)

    return format_mod_column_label(column_format, label_list)


""" for testing on PC """
if not sutron_link:
    column_format = "100 100 100 100\r\n39 77 66 55\r\n"
    label_list = ["H1", "TW", "VB", "RG"]
    reformatted = format_mod_column_label(column_format, label_list)
    print(reformatted)
    expected = "H1: 100; TW: 100; VB: 100; RG: 100\r\nH1: 39; TW: 77; VB: 66; RG: 55\r\n"
    assert(reformatted == expected)
