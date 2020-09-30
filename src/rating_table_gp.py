# Example:  demonstrates an interpolation table  using general purpose variables

"""
The interpolation table uses an 'alpha' value to compute  a 'beta' value.

For discharge computations, this would be a rating table where 'alpha' is stage and 'beta' is discharge.

General Purpose (GP) variables are used to store the table.
The table ends when the next GP variable value is lower than the previous

The interpolation table is stored in GP Value variables.
'GP1 Value' and 'GP2 Value' hold the alpha and beta values for the first table entry.
(GP3, GP4) have the second (alpha, beta) table entry.
With 32 GP variables available, we can hold up to 16 (alpha, beta) pairs::
 table = ((GP1, GP2),
          (GP3, GP4),
          (GP5, GP6),
          (GP7, GP8),
          (GP9, GP10),
          (GP11, GP12),
          (GP13, GP14),
          ..
          (GP29, GP30),
          (GP31, GP32))

Please note that each subsequent alpha value MUST be greater than the previous.
If it is not, the system will stop loading the table. 
Keep the unused parts of the GP Variables at 0.0.

To improve performance, we will load the table from setup whenever
recording is started.  This means that the station needs either a reboot,
or to be stopped and started after changing the GP variables.  
"""

from sl3 import *

# we will load the rating table from GP setup into this variable
# table is said to hold (alpha, beta) pairs
table = [[0, 0],
         [1, 0]]
table_pairs = 2
table_loaded = False


def default_table():
    """writes default values to the table
    table must have at least two entries"""
    global table
    global table_pairs

    table.clear()
    table = [[0, 0],
             [1, 0]]
    table_pairs = 2


@TASK
def load_table():
    """
    Load the table from GP setup.
    Associate this with a script that runs when recording is started.
    """
    global table
    global gp_count
    global table_loaded

    # we stop reading when the alpha value we read is lower than
    # the previous value, indicating end of table

    alpha_one = gp_read_value_by_index(1)
    betaa_one = gp_read_value_by_index(2)
    alpha_two = gp_read_value_by_index(3)
    betaa_two = gp_read_value_by_index(4)

    if alpha_one >= alpha_two:
        # there is not a table in GP variables
        default_table()
        raise ValueError("No table data in GP variables")
    else:
        # the first two alpha values were good - add to table
        table.clear()

        table.append([alpha_one, betaa_one])
        table.append([alpha_two, betaa_two])
        # at this point, we have enough points in the table

        # look through the rest of the gp values, adding to the table
        for i in range(5, gp_count, 2):

            # read in the next pair
            alpha_one = gp_read_value_by_index(i)
            betaa_one = gp_read_value_by_index(i + 1)

            if alpha_one < alpha_two:
                break  # no more valid entries in table
            else:
                # good values.  copy to table
                table.append([alpha_one, betaa_one])

                # copy the previous for later comparison
                alpha_two = alpha_one

    # note that the table is now loaded
    table_loaded = True


@MEASUREMENT
def table_interpol(alpha):
    """
    Given the value alpha, this script will find the closest (alpha, beta) pair in
    the table that is less than the alpha reading, and then perform a linear
    interpolation on the beta values on either side of the alpha value to
    determine the correct beta value. 

    User will need to define the values for the interpolation table based 
    on their application using General Purpose variables which will get loaded
    into global table.

    There are two basic ways configure this script, depending on whether you 
    want both the alpha and beta readings, or just the beta reading.
    
    If you just want the beta reading, attach this function to the alpha measurement.
    If you want both, setup the alpha reading normally, and then setup a second meta 
    measurement.  Have the meta index the alpha reading and have the meta connect
    to this script function.
    """

    global table
    global table_loaded

    # load table if it has not been done already
    if not table_loaded:
        load_table()

    # Test for out of bounds values
    if alpha < table[0][0]:  # below
        beta = table[0][1]  # return first beta
    elif alpha > table[-1][0]:  # above
        beta = table[-1][1]  # return last beta
    else:
        # use for loop to walk through table
        for beta_match in range(len(table)):
            if alpha < table[beta_match][0]:
                break
        beta_match -= 1  # first pair
        # compute linear interpolation
        a_beta1 = table[beta_match][1]
        b_diff_alpha = alpha - table[beta_match][0]
        c_alpha2 = table[beta_match + 1][0]
        d_alpha1 = table[beta_match][0]
        e_flow2 = table[beta_match + 1][1]
        beta = a_beta1 + (b_diff_alpha / (c_alpha2 - d_alpha1)) * (e_flow2 - a_beta1)
    return beta


""" code below is copied from general_purpose.py """

gp_count = 32  # how many general purpose variable sets there are


def gp_index_valid(gp_index):
    """ returns True if the provided general purpose variable index is valid"""
    if (gp_index >= 1) and (gp_index <= gp_count):
        return True
    else:
        return False


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
