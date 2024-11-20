"""
Script logs diagnotic data for Satlink:
lat: latitude in degrees
long: longitude in degrees
batt_tx: battery voltage during last transmission
fwd: forward power during last transmission
ref: reflected power during last transmission

the provided script task log_diag should be scheduled to run a minute or so after TX1 completes
"""

from sl3 import *


def convert_to_decimal_degrees(degrees, minutes, seconds):
    """ converts degrees minutes seconds into degrees with decimal places"""
    result = float(degrees) + float(minutes) / 60.0 + float(seconds) / (60 * 60);
    return result


def gps_parse_lat_long(gps_status):
    """
    Parses Satlink's STATUS GPS looking for the latitude and longitude.

    Example reply when no locati on::

        GPS Sync in progress    GPS tracking satellites
        Clock has NOT been synced to GPS.
        Signal Quality (SatID/Signal CNo): 1/46 3/46 6/43 11/38 17/45 18/36 19/40 22/42 24/37 28/43 at 2018/08/14 15:12:26

    And with location::

        GPS Sync in progress    GPS acquiring almanac
        Last sync to GPS was at 2018/08/14 15:12:48
        Last sync is valid till 2018/09/13 15:12:48
        GPS was powered for 00::00:01:04 before it acquired satellite lock
        Lat N 38o 59' 50.01" Long W 77o 25' 24.46" Alt 134.6m(441.5ft)
        Signal Quality (SatID/Signal CNo): 1/44 3/45 6/41 11/34 17/45 18/35 19/39 22/41 24/34 28/41 at 2018/08/14 15:12:41

    We want this line::

        Lat N 38o 59' 50.01" Long W 77o 25' 24.46" Alt 134.6m(441.5ft)
    """

    # split it into lines
    lines = gps_status.split("\r\n")

    # go through each line, looking for Lat and Long
    found = False
    for lat_long_line in lines:
        if ("Lat" in lat_long_line) and ("Long" in lat_long_line):
            found = True
            break

    if found:
        # strip leading whitespace
        clean_line = lat_long_line.lstrip()

        # split the string into tokens separated by space
        tokens = clean_line.split(' ')

        # this regular expression will match a number at the start of the string
        number_parse = re.compile(r"\d+\.*\d*")

        # parse and convert the numbers to ints and floats
        try:
            lat_deg = int(number_parse.match(tokens[2]).group(0))
            lat_min = int(number_parse.match(tokens[3]).group(0))
            lat_sec = float(number_parse.match(tokens[4]).group(0))

            long_deg = int(number_parse.match(tokens[7]).group(0))
            long_min = int(number_parse.match(tokens[8]).group(0))
            long_sec = float(number_parse.match(tokens[9]).group(0))

            # compute latitude
            latitude = convert_to_decimal_degrees(lat_deg, lat_min, lat_sec)

            # Latitude North means positive degrees, South means negative
            if "Lat S" in lat_long_line:
                latitude = -latitude

            # compute longitude
            longitude = convert_to_decimal_degrees(long_deg, long_min, long_sec)

            # Longitude West means negative degrees
            if "Long W" in lat_long_line:
                longitude = -longitude

            return latitude, longitude

        except ValueError:
            pass
        except IndexError:
            pass

    # if we got this far, our string did not contain the expected numbers
    return 0.0, 0.0


def gps_read_position():
    """
    Gets the current STATUS GPS and parses the location from it.

    :return: latitude, longitude
    :rtype: float, float
    """
    # use the command line to read the gps status
    status = command_line("STATUS GPS", 4 * 1024)

    # pare the location from the status
    return gps_parse_lat_long(status)


def parse_tx_data(text):
    """
    Parse telemetry status to extract battery during tx, forward power, and reflected power.
    Telemetry status is got via the STATUS TX command

    Args:
        text (str): The input text to parse.

    Returns:
        dict: A dictionary with float values and boolean flags indicating success.
    """
    results = {
        "batt_tx": (0.0, False),
        "fwd": (0.0, False),
        "ref": (0.0, False),
    }

    try:
        # Find and extract battery reading
        if "Battery before/during/at end of tx:" in text:
            battery_line = text.split("Battery before/during/at end of tx:")[1].split("\n")[0]
            battery_values = battery_line.split("/")
            if len(battery_values) > 1:
                results["batt_tx"] = (float(battery_values[1]), True)

        # Find and extract forward and reflected power
        if "Forward/reflected power:" in text:
            power_line = text.split("Forward/reflected power:")[1].split("\n")[0]
            power_values = power_line.split("/")
            if len(power_values) > 1:
                results["fwd"] = (float(power_values[0].strip()), True)
                results["ref"] = (float(power_values[1].strip().rstrip("W")), True)

    except ValueError:
        # If any conversion fails, the values will remain (0.0, False)
        pass

    return results


# Example usage
text_tx1_good = """
>STATUS TX
TX1 GOES 300 Scheduled
        Enabled
        Tx succeeded: 1 total, 1 today
        Tx failed: 1 total, 1 today
Last Tx: succeeded at 2024/11/20 12:53:30
        Battery before/during/at end of tx: 12.34/11.84/11.81V
        Forward/reflected power: 1.2/0.0W
        Amp temp before/after: 21.2/21.2C
"""

text_tx2_no_tx = """
TX2 GOES 300 Random
        DISABLED
        Tx succeeded: 0 total, 0 today
        Tx failed: 0 total, 0 today"""

text_sched_good_random_good = """
3 Meas Active
Scheduled Tx: 
	Enabled
	Tx time: 2016/01/22 17:41:00
	Tx succeeded: 17
	Tx failed: 0
Last Tx: succeeded
	Battery before/during/at end of tx: 13.03/12.89/12.73V
	Forward/reflected power: 1.5/0.0W
	Amp temp before/after: 24.4/24.7C
Random Tx: 
	Enabled
	Tx time: 2016/01/22 17:14:29
	Tx succeeded: 19
	Tx failed: 0
Last Tx: succeeded
	Battery before/during/at end of tx: 13.02/12.70/12.76V
	Forward/reflected power: 1.5/0.0W
	Amp temp before/after: 24.3/24.4C
Last Tx was finished at 2016/01/22 16:41:04
"""

test_tx_status_a1 = """
>s tx
TX1 GOES 300 Scheduled
        DISABLED
        Tx succeeded: 1 total, 1 today
        Tx failed: 1 total, 1 today
Last Tx: succeeded at 2024/11/20 12:53:30
        Battery before/during/at end of tx: 12.34/11.84/11.81V
        Forward/reflected power: 1.2/0.0W
        Amp temp before/after: 21.2/21.2C

TX2 GOES 300 Random
        DISABLED
        Tx succeeded: 0 total, 0 today
        Tx failed: 0 total, 0 today


TX3 NOT setup
TX4 NOT setup
TX5 Cell Scheduled
        DISABLED
        Tx succeeded: 0 total, 0 today
        Tx failed: 0 total, 0 today


TX6 NOT setup
TX7 NOT setup
TX8 Cell Scheduled
        Enabled
        Tx succeeded: 11 total, 0 today
        Retx succeeded: 0 total, 0 today
        Tx failed: 0 total, 0 today"""


# code for testing the tx status parser
"""
print(parse_tx_data(text_tx1_good))
print(parse_tx_data(text_tx2_no_tx))
print(parse_tx_data(text_sched_good_random_good))
print(parse_tx_data(test_tx_status_a1))
"""

# have we read the location before?
location_known = False
latitude, longitude = 0.0, 0.0


@TASK
def log_diag():

    global location_known, latitude, longitude

    # get GPS location
    m_latitude, m_longitude = gps_read_position()
    if m_latitude != 0.0 and m_longitude != 0.0:
        latitude = m_latitude
        longitude = m_longitude
        location_known = True

    if location_known:  #either now or a prior reading
        # write location to log
        reading = Reading(label="lat", value=latitude, time=time_scheduled(), etype='E', units="deg")
        reading.write_log()
        reading = Reading(label="long", value=longitude, time=time_scheduled(), etype='E', units="deg")
        reading.write_log()

    # get TX STATUS
    status = command_line("STATUS TX", 4 * 1024)
    parsed_data = parse_tx_data(status)
    if parsed_data["batt_tx"][1]:  # Check if the battery reading is valid
        battery_reading = Reading(
            label="batt_tx",
            value=parsed_data["batt_tx"][0],
            time=time_scheduled(),
            etype="E",
            units="V"
        )
        battery_reading.write_log()

    if parsed_data["fwd"][1]:  # Check if the forward power is valid
        forward_power_reading = Reading(
            label="fwd",
            value=parsed_data["fwd"][0],
            time=time_scheduled(),
            etype="E",
            units="W"
        )
        forward_power_reading.write_log()

    if parsed_data["ref"][1]:  # Check if the reflected power is valid
        reflected_power_reading = Reading(
            label="ref",
            value=parsed_data["ref"][0],
            time=time_scheduled(),
            etype="E",
            units="W"
        )
        reflected_power_reading.write_log()

