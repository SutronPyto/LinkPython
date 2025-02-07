"""
Test module for sunset_sunrise.py
Compares the time of sunrise and sunset produced by our custom sunset_sunrise.py
to pvLib

"""

import sunrise_sunset
import random
from datetime import datetime, timedelta
import pandas as pd
import pvlib
import ephem
import time
import pytz
from timezonefinder import TimezoneFinder

# Latitude ranges from -90 to 90, but errors increase drastically
min_lat, max_lat = -65, 65

# differences are split into two categories to separate software bugs from
# solar time computational errors.   because the custom code will keep
# sunrise and sunset on the same day, a difference of 5 min can look like a difference of 11:55
max_diff_min_limit = 45

max_diff_expected = timedelta(0)
max_diff_wrong_day = timedelta(0)
diff_running_sum = 0.0
diff_samples = 0
diff_major = 0
diff_major_sum = 0.0
total_samples = 0


def get_standard_utc_offset_minutes(dt):
    """
    Given a pytz-aware datetime, return the standard (non-DST) offset in minutes.
    This forces the datetime to use standard time by re-localizing with is_dst=False.
    """
    # If dt is naive or has no offset, assume offset is 0.
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return 0

    # Remove timezone info to get a naive datetime.
    naive = dt.replace(tzinfo=None)
    # Re-localize with is_dst=False to force standard time.
    tz = dt.tzinfo
    dt_std = tz.localize(naive, is_dst=False)
    # Compute and return the offset in minutes.
    return int(dt_std.utcoffset().total_seconds() // 60)


def get_sunrise_sunset_pvlib(latitude, longitude, date):
    # Calculate sunrise and sunset times using pvlib for a given location and date.
    # Define the location using latitude and longitude
    location = pvlib.location.Location(latitude, longitude)

    # Convert the date to a pandas.DatetimeIndex
    date_midnight = pd.DatetimeIndex([date])

    try:
        # Get sunrise, sunset, and solar noon for the given date and location
        times = location.get_sun_rise_set_transit(date_midnight)

        # Extract and return sunrise and sunset
        sunrise = times['sunrise']
        sunset = times['sunset']
        return sunrise[0], sunset[0]

    except ephem.AlwaysUpError:
        # If the sun is always above the horizon (e.g., during polar day)
        print(f"Sun is always up at this location on {date}. No sunset or sunrise.")
        return None, None

    except ephem.NeverUpError:
        # If the sun is always below the horizon (e.g., during polar night)
        print(f"Sun is always down at this location on {date}. No sunset or sunrise.")
        return None, None


def track_diff(diff):
    global max_diff_expected, max_diff_wrong_day, max_diff_min_limit, diff_running_sum, diff_samples, diff_major, diff_major_sum, total_samples
    if diff < timedelta(minutes=max_diff_min_limit):
        diff_samples += 1
        diff_running_sum += diff.total_seconds()
        if diff > max_diff_expected:
            max_diff_expected = diff
    else:
        if diff > max_diff_wrong_day:
            max_diff_wrong_day = diff
        diff_major_sum += diff.total_seconds()
        diff_major += 1
    total_samples += 1


def print_max_diff():
    global max_diff_expected, max_diff_wrong_day, max_diff_min_limit, diff_running_sum, diff_samples, diff_major_sum, total_samples
    print("processed {} samples of sunrise and of sunset\n".format(total_samples))
    if diff_samples:
        print("max diff under {} mins: {}".format(max_diff_min_limit, max_diff_expected))
        avg = (diff_running_sum/diff_samples)/60  # convert to min
        print("avg diff under {} mins: {} mins, over {} sunrise/set times".format(max_diff_min_limit, int(avg), diff_samples))
    else:
        print("no diff under {} mins found".format(max_diff_min_limit))

    if diff_major:
        print("max diff over  {} mins: {}".format(max_diff_min_limit, max_diff_wrong_day))
        avg = (diff_major_sum/diff_major)/60  # convert to min
        print("avg diff over {} mins: {} mins, over {} sunrise/set times".format(max_diff_min_limit, int(avg), diff_major))
    else:
        print("no diff over  {} mins found".format(max_diff_min_limit))


# Comparison function
def compare_sunrise_sunset(latitude, longitude, date_no_local):
    print(f"Location: ({latitude:.4f}, {longitude:.4f})")
    print(f"date noloc:", date_no_local)


    """ major challenge relates to the different time objects
    and their handling of time zone and dst
    custom routines need a time_t timestamp and return the UTC minutes offset from midnight
    pvLib needs a datetime which is properly localized and will use dst
    
    date passed in is a datetime w/o any localization
    """
    global tz_finder

    # ensure date is NOT localized
    if date_no_local.tzinfo is not None and date_no_local.tzinfo.utcoffset(date_no_local) is not None:
        raise ValueError("The datetime is localized; a naive datetime is expected.")

    # convert to timestamp
    timestamp = time.mktime(date_no_local.timetuple())

    # Create a localized datetime without DST adjustments
    timezone_str = tz_finder.timezone_at(lng=longitude, lat=latitude)
    timezone = pytz.timezone(timezone_str)
    localized_date = timezone.localize(date_no_local, is_dst=False)
    print(f"date local:", localized_date)

    # Compute the standard UTC offset in minutes (ignoring DST)
    utc_offset_min = get_standard_utc_offset_minutes(localized_date)
    print(f"utc offset min:", utc_offset_min)

    # compute sunrise, sunset, as the number of minutes since midnight UTC
    sunrise_utc_min, sunset_utc_min = sunrise_sunset.sunrise_sunset_utc_min(
        timestamp, latitude, longitude, verbose=False)

    print(f"sunrise utc H, m:", sunrise_sunset.convert_to_hours_minutes(sunrise_utc_min))
    print(f"sunset utc H, m:", sunrise_sunset.convert_to_hours_minutes(sunset_utc_min))

    # apply utc offset
    sunrise_local_min = sunrise_utc_min + utc_offset_min
    sunset_local_min = sunset_utc_min + utc_offset_min
    print(f"sunrise loc H, m:", sunrise_sunset.convert_to_hours_minutes(sunrise_local_min))
    print(f"sunset locl H, m:", sunrise_sunset.convert_to_hours_minutes(sunset_local_min))

    # normalize to today (UTC offset can change to yesterday or tomorrow)
    sunrise_local_min %= 24*60
    sunset_local_min %= 24*60

    # now, lets take midnight of the localized date
    midnight = localized_date.replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"midnight loc:", localized_date)

    # Add the fractional minutes to get the sunrise datetime
    sunrise_custom = midnight + timedelta(minutes=sunrise_local_min)
    sunset_custom = midnight + timedelta(minutes=sunset_local_min)

    # PVLib method
    sunrise_pvlib, sunset_pvlib = get_sunrise_sunset_pvlib(latitude, longitude, localized_date)

    # if there is a sunrise/sunset, calculate time differences
    if sunrise_pvlib and sunset_pvlib: # sun always up or down.  no sunrise, no sunset
        if sunrise_custom !=0 and sunset_custom != 0: # no sunrise, no sunset
            if (sunrise_pvlib > sunrise_custom):
                sunrise_diff = sunrise_pvlib - sunrise_custom
            else:
                sunrise_diff = sunrise_custom - sunrise_pvlib
            if (sunset_pvlib > sunset_custom):
                sunset_diff = sunset_pvlib - sunset_custom
            else:
                sunset_diff = sunset_custom - sunset_pvlib

            track_diff(sunset_diff)
            track_diff(sunrise_diff)

        # Print comparison
        print(
            f"Custom Sunrise: {sunrise_custom}, PVLib Sunrise: {sunrise_pvlib}, Difference: {str(sunrise_diff).split('.')[0]}")
        print(
            f"Custom Sunset : {sunset_custom}, PVLib Sunset : {sunset_pvlib}, Difference: {str(sunset_diff).split('.')[0]}")
        print()
    else:  # don't have sunrise/set (e.g. north pole in winter)
        print(f"Custom Sunrise: {sunrise_custom}")
        print(f"Custom Sunset : {sunset_custom}")
        print()


# Generate random latitude and longitude
def generate_random_location():
    global min_lat, max_lat
    latitude = random.uniform(min_lat, max_lat)
    longitude = random.uniform(-180, 180)  # Longitude ranges from -180 to 180
    return latitude, longitude


# Generate a random date
def generate_random_datetime():
    # pvLib provides the time of the NEXT sunrise and NEXT sunset (sunrise can be after sunset),
    # whereas the custom code provides the sunrise and sunset of the day in question
    # so always use midnight for the time of day
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    date_only = datetime(random_date.year, random_date.month, random_date.day)
    return date_only


# Run test that https://gml.noaa.gov/grad/solcalc/ defaults to
def test_co_today():
    """ https://gml.noaa.gov/grad/solcalc/
        eqtime min: -13.97
        decl deg:   -15.96
        noon:       12:24:38
        sunrise:    07:28
        sunset:     17:22
        """
    latitude = 45.5152
    longitude = -122.6784
    t = datetime(2025, 2, 6, 12, 0, 0)
    date_only = datetime(t.year, t.month, t.day)
    compare_sunrise_sunset(latitude, longitude, date_only)


def test_au_jan1():
    # australia UTC +10 has Jan 1 while UTC is still Dec 31
    """ https://gml.noaa.gov/grad/solcalc/
        eqtime min: -3.27
        decl deg:   -23.03
        noon:       13:03:15
        sunrise:    05:55
        sunset:     20:12
    """
    latitude = -33
    longitude = 150
    t = datetime(2025, 1, 1, 0, 0, 0)
    compare_sunrise_sunset(latitude, longitude, t)


def test_mktime():
    """
    Location: (-5.9895, 2.7489), Date: 2025-10-24 00:00:00
    """
    t = datetime(2025, 10, 24, 0, 0, 0)
    compare_sunrise_sunset(-5.9895, 2.7489, t)


# Run multiple tests
def run_tests(num_tests=10):
    for _ in range(num_tests):
        latitude, longitude = generate_random_location()
        random_datetime = generate_random_datetime()

        compare_sunrise_sunset(latitude, longitude, random_datetime)


tz_finder = TimezoneFinder()
test_mktime()
test_co_today()
test_au_jan1()
run_tests(1000)
print_max_diff()