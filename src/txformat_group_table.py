# Example:  telemetry data is formatted in group (aka table) mode

"""
This script provides way of formatting telemetry data into CSV group (or table).

For example, given the following XLink default CSV format:
08/28/2024,17:45:25,BATT,11.975,V,G
08/28/2024,17:45:25,TEMP,21.71,C,G
08/28/2024,17:45:25,MINO,1066,,G
08/28/2024,17:45:30,BATT,11.998,V,G
08/28/2024,17:45:30,MINO,1066,,G
08/28/2024,17:45:30,TEMP,21.86,C,G
08/28/2024,17:45:35,BATT,11.983,V,G
08/28/2024,17:45:35,TEMP,21.71,C,G
08/28/2024,17:45:35,MINO,1066,,G

The script will convert the data into group format:
date,time,BATT,MINO,TEMP
08/28/2024,17:45:25,11.975,1066,21.71
08/28/2024,17:45:30,11.998,1066,21.86
08/28/2024,17:45:35,11.983,1066,21.71

The script expects that Tx Format is set to CSV

XLink required setup
!TX1 Data Source=Measurement
!TX1 Format=CSV
!TX1 Custom Script Format=On
!TX1 Format Function=group_format

Please note that XLink testing of this script will fail,
as the test environment does not provide CSV data

"""

from sl3 import *


@TXFORMAT
def group_format(original_flat_csv):
    """
    changes the provided flat csv format into group csv format

    :param original_flat_csv: flat csv format, as created by XLink when Tx Format is CSV
    :return: group formatted csv data, str
    """

    # Split the string into lines
    lines = original_flat_csv.strip().split('\n')

    # Initialize an empty dictionary to store data
    data_dict = {}
    labels = set()

    # Process each line
    for line in lines:
        # Split by commas and unpack the relevant fields
        date, time, label, value, unit, quality = line.strip().split(',')

        # If the timestamp is not in the dictionary, add it
        if (date, time) not in data_dict:
            data_dict[(date, time)] = {}

        # Store the value for the given label under the timestamp
        data_dict[(date, time)][label] = value

        # Add the label to the set of labels
        labels.add(label)

    # Sort labels and timestamps for consistency
    labels = sorted(labels)
    sorted_timestamps = sorted(data_dict.keys())

    # Prepare the output as a string and format up the header
    output_lines = []
    output_lines.append('date,time,' + ','.join(labels))

    # Write each row: date, time + values for each label
    for (date, time) in sorted_timestamps:
        row = [date, time] + [data_dict[(date, time)].get(label, '') for label in labels]
        output_lines.append(','.join(row))

    # Join the output lines into a single string
    output_csv = '\n'.join(output_lines)

    return output_csv


def test_group_formatter():
    csv_data = """
08/28/2024,17:45:25,BATT,11.975,V,G
08/28/2024,17:45:25,TEMP,21.71,C,G
08/28/2024,17:45:25,MINO,1066,,G
08/28/2024,17:45:30,BATT,11.998,V,G
08/28/2024,17:45:30,MINO,1066,,G
08/28/2024,17:45:30,TEMP,21.86,C,G
08/28/2024,17:45:35,BATT,11.983,V,G
08/28/2024,17:45:35,TEMP,21.71,C,G
08/28/2024,17:45:35,MINO,1066,,G"""
    print("input:")
    print(csv_data)

    result = group_format(csv_data)

    print()
    print("converted to group:")
    print(result)


if not sutron_link:  # run tests on PC only
    test_group_formatter()