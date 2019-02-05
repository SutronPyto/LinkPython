# Example:  provides functions to access General Purpose Variables (gp)

""" General Purpose Variable Access
    Please see the user manual for details on gp
    Please ensure SL3 firmware version 8.26 or newer
"""

from sl3 import *

gp_count = 32  # how many general purpose variable sets there are


def gp_index_valid(gp_index):
    """ returns True if the provided general purpose variable index is valid"""
    if (gp_index >= 1) and (gp_index <= gp_count):
        return True
    else:
        return False


def gp_read_label(gp_index):
    """
    Returns the customer set Label of the general purpose variable.

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Label of the specified gp
    :rtype: str
    """
    if gp_index_valid(gp_index):
        return setup_read("GP{} label".format(gp_index))
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_read_value_by_index(gp_index):
    """
    Returns the customer set Value of the general purpose variable.

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Value of the specified p
    :rtype: float
    """
    if gp_index_valid(gp_index):
        return float(setup_read("GP{} value".format(gp_index)))
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_write_label(gp_index, label):
    """
    Writes the Label of the specified gp

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :param label: the new Label for the gp
    :type label: str
    """
    if gp_index_valid(gp_index):
        setup_write("GP{} label".format(gp_index), label)
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_write_value_by_index(gp_index, value):
    """
    Writes the Value of the specified gp

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :param value: the new Value for the gp
    :type value: float
    """
    if gp_index_valid(gp_index):
        setup_write("GP{} value".format(gp_index), value)
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_write_set(gp_index, label, value):
    """
    Writes both the Label and the Value of the specified gp

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :param label: the new Label for the gp
    :type label: str
    :param value: the new Value for the gp
    :type value: float
    """
    gp_write_label(gp_index, label)
    gp_write_value_by_index(gp_index, value)


def gp_find_index(label):
    """
    Tells you the index of the general purpose with said label
    Returns zero if no such label is found

    :param label: the customer set label for the gp
    :type label: string
    :return: gp index if a match is found.  zero if no match is found
    :rtype: int
    """
    for gp_index in range(1, gp_count + 1):
        if label.upper() == gp_read_label(gp_index).upper():
            return gp_index

    return 0  # no gp with that label found


def gp_read_value_by_label(label):
    """
    Returns the Value associated with the Label of the general purpose variable.

    :param label: the user set Label of the general purpose variable
    :type label: str
    :return: the Value of the general purpose variable
    :rtype: float
    """
    gp_index = gp_find_index(label)
    if gp_index_valid(gp_index):
        # we found a match.  return associated value
        gp_value = "GP{} value".format(gp_index)
        return float(setup_read(gp_value))
    else:
        raise ValueError("GP Label not found: ", label)
        return -999.9  # return this if no match is found


def gp_write_value_by_label(label, value):
    """
    Writes a new Value to the general purpose variable associated with the label

    :param label: the user set Label of the general purpose variable
    :type label: str
    :param value: the new Value of the general purpose variable
    :type value: float
    """
    gp_index = gp_find_index(label)
    if gp_index_valid(gp_index):
        # we found a match.  return associated value
        gp_value = "GP{} value".format(gp_index)
        setup_write(gp_value, value)
    else:
        raise ValueError("GP Label not found: ", label)


def gp_read_value(label_or_index):
    """
    Returns the Value associated with the index or Label of the general purpose variable.

    :param label_or_index: either a gp index or the user set Label of the general purpose variable
    :type label_or_index: int or str
    :return: the Value of the general purpose variable
    :rtype: float
    """
    if isinstance(label_or_index, str):
        return gp_read_value_by_label(label_or_index)
    else:
        return gp_read_value_by_index(label_or_index)


def gp_write_value(label_or_index, value):
    """
    Writes a new Value to the general purpose variable

    :param label_or_index: either a gp index or the user set Label of the general purpose variable
    :type label_or_index: int or str
    :param value: the new Value of the general purpose variable
    :type value: float
    """
    if isinstance(label_or_index, str):
        return gp_write_value_by_label(label_or_index, value)
    else:
        return gp_write_value_by_index(label_or_index, value)


def gp_test():
    global sutron_link
    if sutron_link:
        """
        running on embedded system 
        write settings first, then read back and verify
        """
        gp_write_label(1, "Threshold 1")
        gp_write_value_by_index(1, 1.23)

        assert(gp_read_label(1) == "Threshold 1")
        assert(gp_read_value_by_label("Threshold 1") == 1.23)
        assert(gp_read_value_by_index(1) == 1.23)
        assert(gp_read_value("Threshold 1") == 1.23)
        assert(gp_read_value(1) == 1.23)

        gp_write_value_by_label("Threshold 1", -9.87)
        assert(gp_read_value(1) == -9.87)

        gp_write_value(1, 5.56)
        assert(gp_read_value(1) == 5.56)

        gp_write_value("Threshold 1", 8000.0)
        assert(gp_read_value(1) == 8000.0)

        gp_write_set(22, "Nineteen Turtles No", -9.9)
        assert(gp_read_label(22) == "Nineteen Turtles No")
        assert(gp_read_value(22) == -9.9)

        assert(gp_read_label(1) == "Threshold 1")
        assert(gp_read_value("Threshold 1") == 8000.0)

        print("gp test complete")

    else:
        """
        running on PC simulator:
        setup writes are not implemented in the simulator - we just test code flow
        setup reads work in the simulator because they are hardcoded in sl3_sim.py
        """
        gp_write_label(1, "Threshold 1")
        gp_write_value_by_index(1, 1.0)
        gp_write_value_by_label("Threshold 1", 1.0)
        gp_write_value(1, 1.0)
        gp_write_value("Threshold 1", 1.0)
        gp_write_set(1, "Threshold 1", 1.0)

        assert (gp_read_label(1) == "Threshold 1")
        assert (gp_read_value("Threshold 1") == 1.0)
        assert (gp_read_value_by_label("Threshold 1") == 1.0)
        assert (gp_read_value_by_index(1) == 1.0)
        assert (gp_read_value("Threshold 1") == 1.0)
        assert (gp_read_value(1) == 1.0)
