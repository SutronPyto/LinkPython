"""
    Sutron Sat/XLink script for approximating the time of sunrise and sunset
    Please see routine is_daylight for usage

    Code is based upon "General Solar Position Calculations" by "NOAA Global Monitoring Division"
    Code was tested against pvLib for accuracy.
    Errors increase as the location nears the poles
    Under 65 degrees, the worst case erorr was less than 10 mins, average error was ~1 min
    65 to 75 degrees, worst case was ~42min, average ~8min
    above 75 degrees, pvLib disagreed with the NOAA solar calculator https://gml.noaa.gov/grad/solcalc/

    Code was also tested against the NOAA solar calculator at https://gml.noaa.gov/grad/solcalc/


    For Satlink, the GPS provides the latitude and longitude
    For XLink, which has no GPS, please setup the latitude in GP1, longitude in GP2

    !GP1 Label=Latitude
    !GP1 Value=45.515202
    !GP2 Label=Longitude
    !GP2 Value=-122.678398

    If your station is running on local time, the script will automatically use the
        local time offset setting
    If your station is on UTC, the script will need to have the local time offset from UTC
        expressed in minutes setup in GP3.   UTC offset of -08:00 would be -480

    !GP3 Label=time offset min
    !GP3 Value = -480

"""
from sl3 import *
import utime, math


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


def is_leap_year(year):
    """ Determine if a given year is a leap year. """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def fractional_year(day_of_year, hour, year):
    """ Calculate the fractional year (γ) in radians. """
    days_in_year = 366 if is_leap_year(year) else 365
    gamma = (2 * math.pi / days_in_year) * (day_of_year - 1 + (hour - 12) / 24)
    return gamma


def equation_of_time(gamma):
    """ Calculate the equation of time in minutes. """
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    return eqtime


def solar_declination(gamma):
    """ Calculate the solar declination angle in radians. """
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    return decl


def hour_angle_sunrise_sunset(lat_deg, decl_rad):
    """ Calculate the hour angle (ha) for sunrise and sunset.
    based upon the latitude and solar declination angle
    as per the "General Solar Position Calculations" by "NOAA Global Monitoring Division"

    ha = arccos(  cos(zenith)/(cos(lat)*cos(decl)) - tan(lat)*tan(decl) )
    work in radians, not degrees
    """
    lat_rad = math.radians(lat_deg)

    ZENITH_deg = 90.833  # Zenith angle for sunrise/sunset
    ZENITH_rad = math.radians(ZENITH_deg)

    part1 = math.cos(ZENITH_rad) / (math.cos(lat_rad) * math.cos(decl_rad)) - (math.tan(lat_rad) * math.tan(decl_rad))
    part1 = max(min(part1, 1), -1)  # avoid domain errors
    ha_rad = math.acos(part1)
    ha = math.degrees(ha_rad)
    return ha


def calculate_sunrise_sunset(lat, lon, decl, eqtime):
    """ Calculate sunrise and sunset times in minutes from midnight UTC. """
    ha = hour_angle_sunrise_sunset(lat, decl)

    # Calculate sunrise time
    sunrise_time = 720 - 4 * (lon + ha) - eqtime

    # Calculate sunset time
    sunset_time = 720 - 4 * (lon - ha) - eqtime

    return sunrise_time, sunset_time


def convert_to_hours_minutes(minutes):
    hours = int(minutes // 60)
    minutes = int(minutes % 60)
    return hours, minutes


def sunrise_sunset_utc_min(day_time_t, lat_deg, long_deg, verbose=False):
    """
    computes the time of sunrise and sunset for a given day
    the day_time_t needs to be a time during the day, and it needs to be local time
    if day_time_t were in UTC, the result may be for the day before or after
        which will still be within the same accuracy range

    :param day_time_t: day for which to compute the sunrise/set local time, secs since 1970, time_t
    :param lat_deg: latitude of location for sunrise/set, degrees
    :param long_deg: longitude
    :param verbose: controls verbose output for debug
    :return: time of sunrise and sunset expressed in minutes since midnight UTC
    """
    if (lat_deg > 75):
        print("Significant errors appear as the location nears the poles")

    if verbose:
        print("sunrise/sunset computation")
        print("latitude deg: ", lat_deg)
        print("longitude deg: ", long_deg)
        print("date:", ascii_time(day_time_t))

    # Convert timestamp_local to localtime to get day of year
    loc_time = utime.localtime(day_time_t)
    day_of_year = loc_time[7]
    if verbose:
        print("day of year:", day_of_year)

    # Compute fractional year (gamma)
    year = loc_time[0]
    hour = loc_time[3]
    gamma = fractional_year(day_of_year, hour, year)
    if verbose:
        print("gamma:", gamma)

    # Compute equation of time
    eqtime = equation_of_time(gamma)
    if verbose:
        print("eqtime min:", eqtime)

    # Compute solar declination
    decl = solar_declination(gamma)
    if verbose:
        print("decl rad:", decl)
        print("decl deg:", math.degrees(decl))

    # Calculate sunrise, sunset.
    # in minutes from midnight UTC
    sunrise_min, sunset_min = calculate_sunrise_sunset(lat_deg, long_deg, decl, eqtime)
    if sunrise_min == sunset_min:
        if verbose:
            print("Sun always up or down. No sunset or sunrise.")
        return 0.0, 0.0
    else:
        if verbose:
            print("Sunrise UTC:", convert_to_hours_minutes(sunrise_min))
            print("Sunset UTC:", convert_to_hours_minutes(sunset_min))
        return sunrise_min, sunset_min


# stores the results of the previous compuation
last_day_of_year = -1  # the day of year when the computation was last done
last_sunrise_time = 0  # the last computed sunrise time, time_t, local time
last_sunset_time  = 0

def sunrise_sunset_link(day_time_t, lat_deg, long_deg, local_time_offset_min, verbose):
    """
    Sat/XLink routine
    computes the time of sunrise and sunset today
    stores the data globally to optimize.  if called twice for the same day,
    returns the result of previous computation

    the day_time_t needs to be a time during the day, and it needs to be local time

    :param day_time_t: day for which to compute the sunrise/set local time, secs since 1970, time_t
    :param lat_deg: latitude of location for sunrise/set, degrees
    :param long_deg: longitude
    :param local_time_offset_min: offset from UTC in minutes
    :param verbose: controls verbose output for debug
    :return: time of sunrise and sunset expressed in time_t
    """
    global last_day_of_year, last_sunrise_time, last_sunset_time

    # compute the day of the year
    loc_time = utime.localtime(day_time_t)
    day_of_year = loc_time[7]

    if last_day_of_year == day_of_year:
        # we already computed for this day
        if verbose:
            print("Sunrise date:", ascii_time(last_sunrise_time))
            print("Sunset date:", ascii_time(last_sunset_time))
        return last_sunrise_time, last_sunset_time

    # Calculate sunrise, sunset.
    # in minutes from midnight UTC
    sunrise_min, sunset_min = sunrise_sunset_utc_min(day_time_t, lat_deg, long_deg, verbose)

    # extract midnight from the provided day_time_t
    midnight_utc = utime.mktime([loc_time[0], loc_time[1], loc_time[2], 0, 0, 0, 0, 0])
    if verbose:
        print("local time offset min:", local_time_offset_min)

    sunrise_time = midnight_utc + sunrise_min*60 + local_time_offset_min*60
    sunset_time = midnight_utc + sunset_min*60 + local_time_offset_min*60

    if verbose:
        print("Sunrise date:", ascii_time(sunrise_time))
        print("Sunset date:", ascii_time(sunset_time))

    # update globals with new data
    last_day_of_year = day_of_year
    last_sunrise_time = sunrise_time
    last_sunset_time = sunset_time

    return sunrise_time, sunset_time


def sunrise_sunset_time_via_setup(verbose=False):
    """
    gets lat and long and local time offset from setup
    uses current system time
    returns time of sunrise and sunset
    """
    # get location
    found, lat, long = gps_read_position()
    if not found:
        # no GPS, or GPS does not have location
        # read from GP setup
        lat = float(setup_read("GP1 value"))  # latitude is in GP1
        long = float(setup_read("GP2 value"))  # longitude is in GP2

    # get local time offset, expressed in minutes
    local_time_offset = int(setup_read("!LOCAL TIME OFFSET").split()[0])
    if local_time_offset == 0:
        local_time_offset = float(setup_read("GP3 value"))
        if local_time_offset == -1.0:  # default value - user did not set.  also non-sensical time offset
            local_time_offset = 0

    time_local = utime.time()
    sunrise, sunset = sunrise_sunset_link(time_local, lat, long, local_time_offset, verbose)
    return sunrise, sunset


@TASK
def test_via_gp():
    """
    testing routine
    uses info in GP1, 2, 3 to compute sunrise/set
    and prints out result
    """
    # code is optimized to compute only once per day
    # disable that optimization to allow testing
    global last_day_of_year
    last_day_of_year = -1

    sunrise_sunset_time_via_setup(True)


@TASK
def test_daylight():
    """
    used during development to test sunrise and sunset
    known time, lat, long, offset were provided to XLink
    and the results manually checked either against pvLib
    or NOAA solar calc https://gml.noaa.gov/grad/solcalc/
    """

    # sunrise, sunset = sunrise_sunset_link(time_local, lat, long, local_time_offset)
    print('testing daylight')

    """
    Location: (45.5152, -122.6784)
    date local: 2025-02-06 00:00:00-08:00
    Custom Sunrise: 2025-02-06 07:27:20.965717-08:00, PVLib Sunrise: 2025-02-06 07:24:26.164412-08:00, Difference: 0 days 00:02:54
    Custom Sunset : 2025-02-06 17:21:39.828357-08:00, PVLib Sunset : 2025-02-06 17:25:43.646764-08:00, Difference: 0 days 00:04:03
    """
    latitude = 45.5152
    longitude = -122.6784
    time = utime.mktime([2025, 2, 6, 12, 0, 0, 0])
    local_time_offset = -8 * 60
    sunrise_sunset_link(time, latitude, longitude, local_time_offset, True)

    """
    Sunrise date: 12/26/2025,05:25:57
    Sunset date: 12/26/2025,18:52:25
    """
    print('\n')
    latitude = -21.5148
    longitude = 177.6826
    time = utime.mktime([2025, 12, 26, 0, 0, 0, 0])
    local_time_offset = 12 * 60
    sunrise_sunset_link(time, latitude, longitude, local_time_offset, True)

    """
    Location: (32.1396, -101.0694)
    date local: 2025-02-13 00:00:00-06:00
    utc offset min: -360
    Custom Sunrise: 2025-02-13 07:29:55.199524-06:00, PVLib Sunrise: 2025-02-13 07:27:48.605046-06:00, Difference: 0 days 00:02:06
    Custom Sunset : 2025-02-13 18:27:07.229774-06:00, PVLib Sunset : 2025-02-13 18:29:26.345073-06:00, Difference: 0 days 00:02:19
    """
    print('\n')
    latitude = 32.1396
    longitude = -101.0694
    time = utime.mktime([2025, 2, 13, 0, 0, 0, 0])
    local_time_offset = -360
    sunrise_sunset_link(time, latitude, longitude, local_time_offset, True)

    """
    Sunrise 10:15 Sunset 15:45
    """
    print('\n')
    latitude = 61.217379
    longitude = -149.80957
    time = utime.mktime([2025, 12, 26, 12, 0, 0, 0])
    local_time_offset = -9 * 60
    sunrise_sunset_link(time, latitude, longitude, local_time_offset, True)

    """ Sunrise 6:55, set 18:17 """
    print('\n')
    latitude = 19.725342
    longitude = -155.43457
    time = utime.mktime([2025, 2, 6, 14, 40, 5, 0])
    local_time_offset = -10 * 60
    sunrise_sunset_link(time, latitude, longitude, local_time_offset, True)


def is_daylight(before_sunrise_sec=0, after_sunset_sec=0):
    """
    returns True if it is currently daylight

    :param before_sunrise_sec: how many seconds before sunrise is there daylight?
    :param after_sunset_sec: how many seconds after sunset is there daylight?

    :return: True if between sunrise and sunset
    """
    time_local = utime.time()
    sunrise, sunset = sunrise_sunset_time_via_setup()

    if (sunrise - before_sunrise_sec) < time_local < (sunset + after_sunset_sec):
        return True  # daylight
    else:
        return False


@MEASUREMENT
def is_daylight_meas(ignored):
    """
    returns 1 if it is currently daylight, 0 if dark
    """
    before_sunrise_sec = 900
    after_sunset_sec = 900
    if is_daylight(before_sunrise_sec, after_sunset_sec):
        print("Daylight")
        return 1
    else:
        print("Darkness")
        return 0

