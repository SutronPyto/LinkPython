# Example:  GPS Position Logging Program
"""
Latitude and longitude are recorded as measurements.

A script task runs periodically:
    * Task ensures the GPS is on
    * Task reads the  position for the GPS and stores it into global variables
Two measurements are associated with scripts:
    * One reads the latitude from the global variable
    * The other reads the longitude from the global variable
    * The measurements need to be scheduled right after the script task
A setup file is associated with this script!
"""

import re
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
    return gps_parse_lat_long(status )


def test_gps_read_position():
    """ Verifies that gps_read_position works"""

    str1 = \
        "GPS Sync in progress    GPS acquiring almanac\r\n\
        Last sync to GPS was at 2018/08/14 15:12:48\r\n\
        Last sync is valid till 2018/09/13 15:12:48\r\n\
        GPS was powered for 00::00:01:04 before it acquired satellite lock\r\n\
        Lat N 38o 59' 50.01\" Long W 77o 25' 24.46\" Alt 134.6m(441.5ft)\r\n\
        Signal Quality (SatID/Signal CNo): 1/44 3/45 6/41 11/34 17/45 18/35 19/39 22/41 24/34 28/41 at 2018/08/14 15:12:41\r\n\
        "
    lat, long = gps_parse_lat_long(str1)

    # compare the floating point values by subtracting them and
    # verifying the difference is insignificant
    assert ((lat - 38.99723) < 0.001)
    assert ((long - -77.42346) < 0.001)

    str2 = ""
    lat, long = gps_parse_lat_long(str2)

    # compare the floating point values by subtracting them and
    # verifying the difference is insignificant
    assert (lat == 0.0)
    assert (long == 0.0)


# we need to check the version of Satlink firmware
version_needs_check = True

""" In order to assure that both latitude and longitude are
read at the same time, we will have a Satlink task read the
GPS status and store the latitude and longitude globally."""
m_latitude = 0.0
m_longitude = 0.0

@TASK
def gps_keep_on_and_read_position():
    """
    Task has two functions:
        * Make sure the GPS stays on all the time
        * Read the position from the GPS and store it in globals

    Task should be scheduled to run periodically, every 5 minutes.

    It should happen 30 seconds before the latitude and longitude meas.
    """

    # The listen command will tell the system to keep GPS on
    command_line("!LISTEN 3600")

    # This command will tell the GPS to acquire time and location
    command_line("!GPS SYNC")

    # Give the GPS a chance to complete the position acquisition
    if not is_being_tested():  # if we are testing the scirpt, don't wait
        utime.sleep(25.0)

    # Read the GPS position and store it
    global m_latitude
    global m_longitude
    m_latitude, m_longitude = gps_read_position()

    # Requires Satlink version 2916 or newer
    global version_needs_check
    if version_needs_check:
        if ver()[2] < 2974:
            raise AssertionError("Upgrade Satlink firmware!")
        else:
            version_needs_check = False


@MEASUREMENT
def meas_latitude(inval):
    """Associate with a measurement to have it log latitude.
    The measurement should be setup as manual entry.

    Please note that this returns a result of zero until
    the task gps_keep_on_and_read_position is run"""
    return m_latitude


@MEASUREMENT
def meas_longitude(inval):
    """ Like meas_latitude, but for longitude"""
    return m_longitude
