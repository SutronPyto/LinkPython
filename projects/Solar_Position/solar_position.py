""" computes solar position based upon current time and location for Sat/XLink
    code based on https://github.com/pvlib/pvlib-python/blob/main/pvlib/solarposition.py


    For Satlink, the GPS provides the latitude and longitued
    For XLink, which has no GPS, please setup the latitude in GP1, longitude in GP2

    !GP1 Label=Latitude
    !GP1 Value=45.515202
    !GP2 Label=Longitude
    !GP2 Value=-122.678398

    Position information has been verified with NOAA solar calculator
    Additionally, the companion file solar_position_test.py tests code against pvlib
"""

from sl3 import *
import math
import utime


def days_in_year(year):
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return 366
    else:
        return 365


def solar_pos_ephemeris(timestamp, latitude, longitude, pressure=101325, temperature=12):
    """
    Python-native solar position calculator.
    The accuracy of this code is not guaranteed.
    Consider using the built-in spa_c code or the PyEphem library.

    Parameters
    ----------
    timestamp : utime.time (UTC timestamp, sec since 1970)
    latitude : float
        Latitude in decimal degrees. Positive north of equator, negative
        to south.
    longitude : float
        Longitude in decimal degrees. Positive east of prime meridian,
        negative to west.
    pressure : float or Series, default 101325
        Ambient pressure (Pascals)
    temperature : float or Series, default 12
        Ambient temperature (C)

    Returns
    -------

    DataFrame with the following columns:

        * apparent_elevation : apparent sun elevation accounting for
          atmospheric refraction.
        * elevation : actual elevation (not accounting for refraction)
          of the sun in decimal degrees, 0 = on horizon.
          The complement of the zenith angle.
        * azimuth : Azimuth of the sun in decimal degrees East of North.
          This is the complement of the apparent zenith angle.
        * apparent_zenith : apparent sun zenith accounting for atmospheric
          refraction.
        * zenith : Solar zenith angle
        * solar_time : Solar time in decimal hours (solar noon is 12.00).

    References
    -----------

    .. [1] Grover Hughes' class and related class materials on Engineering
       Astronomy at Sandia National Laboratories, 1985.

    See also
    --------
    pyephem, spa_c, spa_python

    """

    # Added by Rob Andrews (@Calama-Consulting), Calama Consulting, 2014
    # Edited by Will Holmgren (@wholmgren), University of Arizona, 2014

    # Most comments in this function are from PVLIB_MATLAB or from
    # pvlib-python's attempt to understand and fix problems with the
    # algorithm. The comments are *not* based on the reference material.
    # This helps a little bit:
    # http://www.cv.nrao.edu/~rfisher/Ephemerides/times.html

    # the inversion of longitude is due to the fact that this code was
    # originally written for the convention that positive longitude were for
    # locations west of the prime meridian. However, the correct convention (as
    # of 2009) is to use negative longitudes for locations west of the prime
    # meridian. Therefore, the user should input longitude values under the
    # correct convention (e.g. Albuquerque is at -106 longitude), but it needs
    # to be inverted for use in the code.

    """ Copied from pvlib in Sept 2024, 
    https://github.com/pvlib/pvlib-python/blob/main/pvlib/solarposition.py
    And converted to work without pandas, numpy, datetime for use
    with the Sutron Sat/XLink product line by OTT Hydromet"""

    Longitude = -1 * longitude

    Abber = 20 / 3600.
    LatR = math.radians(latitude)

    # Convert timestamp to localtime (which has day of year etc)
    loc_time = utime.localtime(timestamp)

    # Day of the year
    day_of_year = loc_time[7]

    # Decimal hours
    decimal_hours = loc_time[3] + loc_time[4] / 60. + loc_time[5] / 3600.

    # Year calculations for celestial mechanics
    yr_since_1900 = loc_time[0] - 1900
    yr_begin = 365 * yr_since_1900 + (yr_since_1900 - 1) // 4 - 0.5

    e_zero = yr_begin + day_of_year
    t = e_zero / 36525.

    # Greenwich Mean Sidereal Time (GMST)
    gmst0 = (6 / 24. + 38 / 1440. + (45.836 + 8640184.542 * t + 0.0929 * t ** 2) / 86400.) % 1.0
    gmst0_deg = 360 * gmst0
    gmsti_deg = (gmst0_deg + 360 * (1.0027379093 * decimal_hours / 24.)) % 360

    # Local apparent sidereal time
    loc_ast_deg = (360 + gmsti_deg - Longitude) % 360

    # More celestial mechanics
    epoch_date = e_zero + decimal_hours / 24.
    t1 = epoch_date / 36525.

    # Obliquity of the ecliptic
    obliquity_r = math.radians(23.452294 - 0.0130125 * t1 - 1.64e-06 * t1 ** 2 + 5.03e-07 * t1 ** 3)

    # Eccentricity and anomaly
    ml_perigee = (281.22083 + 4.70684e-05 * epoch_date + 0.000453 * t1 ** 2 + 3e-06 * t1 ** 3) % 360
    mean_anom = (358.47583 + 0.985600267 * epoch_date - 0.00015 * t1 ** 2 - 3e-06 * t1 ** 3) % 360
    eccen = 0.01675104 - 4.18e-05 * t1 - 1.26e-07 * t1 ** 2
    eccen_anom = mean_anom

    # Solve Kepler's equation iteratively
    eccen_anom_prev = 0
    while abs(eccen_anom - eccen_anom_prev) > 0.0001:
        eccen_anom_prev = eccen_anom
        eccen_anom = mean_anom + math.degrees(eccen) * math.sin(math.radians(eccen_anom))

    # True anomaly
    true_anom = 2 * math.degrees(
        math.atan2(math.sqrt((1 + eccen) / (1 - eccen)) * math.tan(math.radians(eccen_anom) / 2), 1))

    # Ecliptic longitude
    ec_lon = (ml_perigee + true_anom) % 360 - Abber
    ec_lon_r = math.radians(ec_lon)

    # Declination and right ascension
    dec_r = math.asin(math.sin(obliquity_r) * math.sin(ec_lon_r))
    rt_ascen = math.degrees(math.atan2(math.cos(obliquity_r) * math.sin(ec_lon_r), math.cos(ec_lon_r)))

    # Hour angle
    hr_angle = loc_ast_deg - rt_ascen
    hr_angle = hr_angle - 360 if abs(hr_angle) > 180 else hr_angle
    hr_angle_r = math.radians(hr_angle)

    # Solar azimuth and elevation
    sun_az = math.degrees(
        math.atan2(-math.sin(hr_angle_r), math.cos(LatR) * math.tan(dec_r) - math.sin(LatR) * math.cos(hr_angle_r)))
    if sun_az < 0:
        sun_az += 360

    sun_el = math.degrees(
        math.asin(math.cos(LatR) * math.cos(dec_r) * math.cos(hr_angle_r) + math.sin(LatR) * math.sin(dec_r)))

    # Refraction correction
    refraction = 0.0
    if sun_el > 5:
        refraction = 58.1 / math.tan(math.radians(sun_el)) - 0.07 / (math.tan(math.radians(sun_el)) ** 3) + 0.000086 / (
                math.tan(math.radians(sun_el)) ** 5)
    elif sun_el > -0.575:
        refraction = sun_el * (-518.2 + sun_el * (103.4 + sun_el * (-12.79 + sun_el * 0.711))) + 1735
    elif sun_el > -1:
        refraction = -20.774 / math.tan(math.radians(sun_el))

    refraction *= (283 / (273 + temperature)) * (pressure / 101325) / 3600

    apparent_sun_el = sun_el + refraction

    return {
        'apparent_elevation': apparent_sun_el,
        'elevation': sun_el,
        'azimuth': sun_az,
        'apparent_zenith': 90 - apparent_sun_el,
        'zenith': 90 - sun_el,
        'solar_time': (180 + hr_angle) / 15

    }


def print_sol_result(utc_timestamp, latitude, longitude, sol_result):
    """
    prints the times, lat, long and all the results produced by solar position
    """
    print("Location latitude: {:.2f}, longitude: {:.2f}, UTC time: {},".format(
        latitude, longitude, ascii_time(utc_timestamp)))
    for key in sol_result:
        print("{}: {:.2f}".format(key, sol_result[key]))


@TASK
def test_sol():
    latitude = 40
    longitude = 105
    utc_timestamp = utime.mktime([2024, 9, 5, 19, 50, 35])
    sol_result = solar_pos_ephemeris(utc_timestamp, latitude, longitude)
    print(utc_timestamp, latitude, longitude, sol_result)


def convert_to_decimal_degrees(degrees, minutes, seconds):
    """ converts degrees minutes seconds into degrees with decimal places"""
    result = float(degrees) + float(minutes) / 60.0 + float(seconds) / (60 * 60);
    return result


def gps_parse_lat_long(gps_status):
    """
    :param gps_status: Satlink's reply to STATUS GPS
    :return: GPS found, latitude, longitude
    :rtype: bool, float, float

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

            return True, latitude, longitude

        except ValueError:
            pass
        except IndexError:
            pass

    # if we got this far, our string did not contain the expected numbers
    return False, 0.0, 0.0


def gps_read_position():
    """
    Gets the current STATUS GPS and parses the location from it.
    Handles situation where there is no GPS on board for XLink

    :return: GPS found, latitude, longitude
    :rtype: bool, float, float
    """
    # use the command line to read the gps status
    status = command_line("STATUS GPS", 4 * 1024)

    # pare the location from the status
    return  gps_parse_lat_long(status )


@TASK
def solar_position():
    """
    illustrates the use of solar position function
    as well as reading the geolocation from the GPS or
    alternatively from GP settings
    """

    found, lat, long = gps_read_position()
    if not found:
        # no GPS, or GPS does not have location
        # read from GP setup
        lat = float(setup_read("GP1 value"))  # latitude is in GP1
        long = float(setup_read("GP2 value"))  # longitude is in GP2

    local_time_offset = int(setup_read("!LOCAL TIME OFFSET").split()[0])
    time_local = utime.time()
    time_utc = time_local - local_time_offset*60  # time offset is in minutes

    sol_result = solar_pos_ephemeris(time_utc, lat, long)

    print_sol_result(time_utc, lat, long, sol_result)


