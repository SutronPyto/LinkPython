from sl3 import *
import json
from ucollections import OrderedDict

"""
Setup instructions::

1. Set the station name of the XLink to the device ID configured 
   in your MQTT broker.

2. The TX(n) fields which should be configured via LinkComm are:
    Enable                  [x]
    Radio type:             [Cell]
    Kind:                   [Scheduled]
    Scheduled time:         [           ]
    Scheduled interval:     [           ]
    Custom script format:   [x]
    Script format function: [JSON_TxFormat]

3. In addition measurements should be configured and enabled to be 
   transmitted via Telemetry(n).

4. The following General Purpose Variables should be defined via 
   LinkComm in order to transmit the station's location (you can edit
   the variables by clicking the "Edit Variables..." button in the "Other Setup"
   screen under the "General Purpose Variables" section) :

    Variable    Label       Value (sample)
    ========    ==========  =============
    GP1         Latitude    38.996983
    GP2         Longitude   -77.424065
    GP3         Elevation   88.000000

Note: the JSON_TxFormat function will only format 100 lines of CSV data, this can be adjusted
      with the `CSV_LIMIT` variable below:
"""

# Limit the number of CSV lines to format
CSV_LIMIT = 100


def read_variable(match, default=None):
    """
    Look for a GP variable by the name of 'match', return "<match> not configured" if it can't be found

    :param match: The name of the variable to find
    :param default: The default value to return if the variable is not found
    :return: The value of the variable or a default message if not found
    """
    try:
        result = next(setup_read("GP{} value".format(i)) for i in range(1, 33) if
                      setup_read("GP{} label".format(i)).lower() == match)
    except (StopIteration, ValueError):
        if default:
            result = default
        else:
            result = "{} not configured".format(match)
    return result


def read_variable_float(match, default=None):
    """
    Look for a GP variable by the name of 'match', return "<match> not configured" if it can't be found

    :param match: The name of the variable to find
    :param default: The default value to return if the variable is not found
    :return: The value of the variable as a float or a default message if not found
    """
    try:
        result = float(next(setup_read("GP{} value".format(i)) for i in range(1, 33) if
                            setup_read("GP{} label".format(i)).lower() == match))
    except (StopIteration, ValueError):
        if default:
            result = default
        else:
            result = "{} not configured".format(match)
    return result


def format_ISO8601(date, time, time_offset_minutes):
    """
    Convert a date and time to ISO8601 format

    :param date: The date in MM/DD/YYYY format
    :param time: The time in HH:MM:SS format
    :param time_offset_minutes: The local time offset from GMT in minutes
    :return: The date and time in ISO8601 format
    """
    if time_offset_minutes > 0:
        result = "{}-{}-{}T{}+{:02}{:02}".format(date[6:10], date[0:2], date[3:5], time,
                                                 time_offset_minutes // 60, time_offset_minutes % 60)
    elif time_offset_minutes < 0:
        result = "{}-{}-{}T{}-{:02}{:02}".format(date[6:10], date[0:2], date[3:5], time,
                                                 -time_offset_minutes // 60, -time_offset_minutes % 60)
    else:
        result = "{}-{}-{}T{}Z".format(date[6:10], date[0:2], date[3:5], time)
    return result


def json_format(csv, logger_id, station_name, time_offset_minutes=0, missing_flag="MISSING"):
    """
    Converts a string of observations in the format:

    09/20/2023,11:14:45,AT,26.65,,G
    09/20/2023,11:14:45,BP,96.65,,G
    09/20/2023,11:14:30,AT,26.68,,G
    09/20/2023,11:14:30,BP,97.33,,G

    to a dictionary of the format:

    {
      "properties": {
        "observationNames": [
          "AT",
          "BP",
        ],
        "observations": {
          "2023-09-20T11:14:30Z": [
            26.68,
            26.65,
          ],
          "2023-09-20T11:14:45Z": [
            97.33,
            96.65,
          ],
        }
      }
    }

    :param csv: A list of comma-separated strings containing the formatted values
    :param logger_id: Expect USState_StationID_DeviceID_SensorID but something like (ex: "VA_12345678_XL2_12345")
    :param station_name: If not blank, is included in the observations as "StationName"
    :param time_offset_minutes: The local time offset from GMT in minutes
    :param missing_flag: What to use to indicate missing readings
    :return: A dictionary containing the observations, sorted by time and grouped by name
    """
    names = []
    observations = {}

    # Parse the CSV values into a dictionary keyed on time and sensor name for easy access
    for line in csv:
        date, time, name, value, units, quality = line.split(",")

        # Convert "09/21/2023", "11:29:45" to "2023-09-21T11:29:45-0500"
        time = format_ISO8601(date, time, time_offset_minutes)

        # Convert the value to a number if possible, otherwise leave it as a string
        try:
            value = float(value)
        except ValueError:
            pass

        # Add the name to the list of all names in the message if it's not already in it
        if name not in names:
            names.append(name)

        # Add the time to the observations if it doesn't already exist
        if time not in observations:
            observations[time] = {}

        # Add the sensor name to the observations if it doesn't already exist
        if name not in observations[time]:
            observations[time][name] = {}

        # Add the observed value to the observations
        observations[time][name] = value

    # Ensure there's an entry for every sensor and sort the data based on sensor name
    for time in observations:
        for name in names:
            if name not in observations[time]:
                observations[time][name] = missing_flag
        observations[time] = OrderedDict(sorted(observations[time].items()))

    # Sort the names
    names.sort()

    # Add StationName to the names
    if station_name:
        names += ["StationName"]

    # Sort all the observations based on time
    observations = OrderedDict(sorted(observations.items()))

    # Remove the sensor names from the observations because they are reported separately
    # in the "observationNames" key and the order is assumed from that:
    for key, data in observations.items():
        observations[key] = list(data.values())
        if station_name:
            observations[key] += [station_name]

    return {"properties": {"loggerID": logger_id, "observationNames": names, "observations": observations}}


@TXFORMAT
def JSON_TxFormat(t):
    """
    Format the telemetry data into JSON format for transmission.

    :param t: The telemetry data as a string
    :return: The formatted JSON string
    """
    # If the script is being tested, then substitute some fixed data
    if t == "This is a test message":
        t = "09/20/2023,11:14:45,AT,26.65,,G\n" \
            "09/20/2023,11:14:45,BP,96.65,,G\n" \
            "09/20/2023,11:14:30,AT,26.68,,G\n" \
            "09/20/2023,11:14:30,BP,97.33,,G\n"

    # Limit the formatting to the first 100 items (comment out this line if you do not want this limit)
    t = t.split()[:CSV_LIMIT]

    station_name = setup_read("station name")
    # We are using the station_name as the logger_id in this demo
    # and hence individual observations are not labelled with the
    # station ID
    logger_id = station_name
    missing_flag = "MISSING"
    time_offset_minutes = int(setup_read("local time offset").split()[0])

    # Create the header for the JSON message
    header = {
        "type": "Feature",
        "geometry":
            {
                "type": "Point",
                "coordinates":
                    [
                        read_variable_float("longitude"),
                        read_variable_float("latitude"),
                        read_variable_float("elevation"),
                    ],
            }}

    # Format the body of the JSON message
    body = json_format(t, logger_id, "", time_offset_minutes, missing_flag)

    # Combine the header and body into a single message
    message = OrderedDict()
    message.update(header)
    message.update(body)

    # Convert the message to a JSON string and return it
    return json.dumps(message)
