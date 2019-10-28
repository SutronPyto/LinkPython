# Example:  Computes evapotranspiration

"""
This module is used to compute daily potential evapotranspiration (ET) based on
American Society of Civil Engineers standardized reference evapotranspiration equation (January 2005)

A Sat/XLink setup is associated with this module:
`evapotranspiration_setup.txt <evapotranspiration_setup.txt>`_

The provided setup makes hourly sensor readings.  The interval may be modified to suit your station.
However, ET must be computed daily to be accurate.

The following sensor readings and associated units are used to compute ET:

* Air temperature (AT).  Units may be
    * 'C' for Celsius (default)
    * 'F' for 'Fahrenheit'
* Relative humidity (RH) expressed in percent.
* Barometric pressure (BP).  Units:
    * 'mb' for millibar (default)
    * 'Hg' for inches of mercury
* Solar radiation (RI).  Units:
    * 'Wm2' for Watts per meters squared
    * 'Lyd' for Langleys per day (1 Lyd = 0.484583 Wm2) (default)
    * 'Lyh' for Langleys per hour
    * 'Lym' for Langleys per minute
* Wind speed (WS).  Units:
    * 'kph' for kilometers per hour (default)
    * 'mph' for miles per hour
    * 'mps' for meters per second
    * 'kn' for knots
    * 'fps' for feet per second
* Daily Evapotranspiration (ET) is the result.  Units may be
    * 'cm' (default)
    * 'mm'
    * 'in'

Please change the sensor units in the setup to one of the units listed.  The system will use default units otherwise.

Please make sure the ET measurement is scheduled after all sensor readings are complete,
e.g. set the measurement time to 5 min.
If that is not an option, uncomment utime.sleep at start of compute_ET routine.

If recording is OFF, counts get reset every time ET is measured.  This allows for testing.
If recording is ON, counts get reset when a scheduled ET measurement is made.

If recording is ON, and a live (forced) measurement of one of the 5 sensors takes place, it will NOT count towards ET.
This allows making live readings without interfering with ET.

The ET calculation method used is based on:
Me. Jensen, R. D. Burman, and R. G. Allen 1990.
Evapotranspiration and Irrigation water Requiremtnts
ASCE manuals and Reports on Engineering Practice NO.70
American Society of Civil Engineers NY 1-332
Walter, et. al. January 2005
The ASCE Standardized Reference Evapotranspiration Equation
ASCE-EWRI Task Committee Report
ASCE-EWRI Task Committee Report Appendixes A-C
"""

output_ET = 'ETo'
""" Change the variable above to control the type of ET to compute. Choices:
'ETo' for Standardized Reference Evapotranspiration, short grass
'ETr' for Standardized Reference Evapotranspiration, tall alfalfa
'ETWater' Same as ETo except uses albedo of 0.06, characteristic of open water
"""

wind_elevation = 2.0
""" Wind Elevation in meters at which wind measurements are taken. """


# Development and diagnostic settings:
print_all_samples = False  # prints every sample of every sensor
print_results = True  # prints sensor averages and results of computation


from sl3 import *
import utime


# These variables store the units used.
# Do not change here but use standard LinkComm setup instead.
units_AT = ""
units_BP = ""
units_RI = ""
units_WS = ""
units_ET = ""

# We store the sensor readings for the ET computation below
# We count and sum up the readings as they come in

# air temperature
at_cnt = 0  # how many AT readings so far?
at_sum = 0.0  # sum of AT readings
at_min = 0.0  # AT minimum
at_max = 0.0  # AT maximum

# relative humidity in percent (we only need min and max, not avg)
rh_cnt = 0
rh_min = 0.0
rh_max = 0.0

# barometric pressure
bp_cnt = 0
bp_sum = 0.0

# solar radiation
ri_cnt = 0
ri_sum = 0.0

# wind speed
ws_cnt = 0
ws_sum = 0.0


@TASK
def reset_ET():
    """
    Call function to clear out past averages and restart computation
    """
    global at_cnt
    global rh_cnt
    global bp_cnt
    global ri_cnt
    global ws_cnt

    at_cnt = 0
    rh_cnt = 0
    bp_cnt = 0
    ri_cnt = 0
    ws_cnt = 0


# we need to check the version of Satlink firmware
version_needs_check = True


@TASK
def version_check():
    """
    Ensures firmware supports this script
    """
    # Requires Satlink version 8.28r3097 or newer
    global version_needs_check
    if version_needs_check:
        if ver()[2] < 3097:
            raise AssertionError("Upgrade Satlink firmware to 8.28 r3097 or newer!")
        else:
            version_needs_check = False


@MEASUREMENT
def meas_AT(sensor_reading):
    """
    Connect this to the air temperature reading
    The routine will compute min, max, and average
    """
    global at_cnt
    global at_sum
    global at_min
    global at_max

    if not is_meas_valid():
        return sensor_reading  # bad sample

    # a live reading while running will NOT be counted towards ET
    # lest it interfere with the ET computation
    if not is_scheduled():
        if setup_read("Recording").upper() == "ON":
            return sensor_reading

    lock()  # multi-thread protection
    if at_cnt == 0:
        # first reading
        at_sum = sensor_reading
        at_min = sensor_reading
        at_max = sensor_reading
    else:
        at_sum += sensor_reading
        if sensor_reading > at_max:
            at_max = sensor_reading
        elif sensor_reading < at_min:
            at_min = sensor_reading
    at_cnt += 1
    unlock()

    # read units from setup
    if not is_being_tested():  # tests do not have proper setups
        global units_AT
        units_AT = setup_read("M{} Units".format(index()))

    if print_all_samples:
        print("AT sample {}: {} {}".format(at_cnt, sensor_reading, units_AT))

    return sensor_reading


@MEASUREMENT
def meas_BP(sensor_reading):
    """
    Connect this to the barometric pressure  measurement
    The routine will compute average for use in ET
    Additionally, Sat/XLink version check is made
    """
    global bp_cnt
    global bp_sum

    version_check()

    if not is_meas_valid():
        return sensor_reading  # bad sample

    # a live reading while running will NOT be counted towards ET
    # lest it interfere with the ET computation
    if not is_scheduled():
        if setup_read("Recording").upper() == "ON":
            return sensor_reading

    lock()  # multi-thread protection
    if bp_cnt == 0:
        # first reading
        bp_sum = sensor_reading
    else:
        bp_sum += sensor_reading
    bp_cnt += 1
    unlock()

    # read units from setup
    if not is_being_tested():  # tests do not have proper setups
        global units_BP
        units_BP = setup_read("M{} Units".format(index()))

    if print_all_samples:
        print("BP sample {}: {} {}".format(bp_cnt, sensor_reading, units_BP))

    return sensor_reading


@MEASUREMENT
def meas_RH(sensor_reading):
    """
    Connect this to the relative humidity  measurement
    The routine will compute average for use in ET
    """
    global rh_cnt
    global rh_min
    global rh_max

    if not is_meas_valid():
        return sensor_reading  # bad sample

    if (sensor_reading > 100.0) or (sensor_reading < 0.0):
        return sensor_reading  # out of bounds

    # a live reading while running will NOT be counted towards ET
    # lest it interfere with the ET computation
    if not is_scheduled():
        if setup_read("Recording").upper() == "ON":
            return sensor_reading

    lock()  # multi-thread protection
    if rh_cnt == 0:
        # first reading
        rh_min = sensor_reading
        rh_max = sensor_reading
    else:
        if sensor_reading > rh_max:
            rh_max = sensor_reading
        elif sensor_reading < rh_min:
            rh_min = sensor_reading
    rh_cnt += 1
    unlock()

    if print_all_samples:
        print("RH sample {}: {} %".format(bp_cnt, sensor_reading))

    return sensor_reading


@MEASUREMENT
def meas_RI(sensor_reading):
    """
    Connect this to the solar radiation measurement
    The routine will compute average for use in ET
    """
    global ri_cnt
    global ri_sum

    if not is_meas_valid():
        return sensor_reading  # bad sample

    # a live reading while running will NOT be counted towards ET
    # lest it interfere with the ET computation
    if not is_scheduled():
        if setup_read("Recording").upper() == "ON":
            return sensor_reading

    lock()  # multi-thread protection
    if ri_cnt == 0:
        # first reading
        ri_sum = sensor_reading
    else:
        ri_sum += sensor_reading
    ri_cnt += 1
    unlock()

    # read units from setup
    if not is_being_tested():  # tests do not have proper setups
        global units_RI
        units_RI = setup_read("M{} Units".format(index()))

    if print_all_samples:
        print("RI sample {}: {} {}".format(ri_cnt, sensor_reading, units_RI))

    return sensor_reading


@MEASUREMENT
def meas_WS(sensor_reading):
    """
    Connect this to the wind speed measurement
    The routine will compute average for use in ET
    """
    global ws_cnt
    global ws_sum

    if not is_meas_valid():
        return sensor_reading  # bad sample

    # a live reading while running will NOT be counted towards ET
    # lest it interfere with the ET computation
    if not is_scheduled():
        if setup_read("Recording").upper() == "ON":
            return sensor_reading

    lock()  # multi-thread protection
    if ws_cnt == 0:
        # first reading
        ws_sum = sensor_reading
    else:
        ws_sum += sensor_reading
    ws_cnt += 1
    unlock()

    # read units from setup
    if not is_being_tested():  # tests do not have proper setups
        global units_WS
        units_WS = setup_read("M{} Units".format(index()))

    if print_all_samples:
        print("WS sample {}: {} {}".format(ws_cnt, sensor_reading, units_WS))

    return sensor_reading


@MEASUREMENT
def compute_ET(ignored):
    """ Computes ET based on data in global variables
    Associate this with the ET measurement
    :param ignored: this variable is not used
    :return: ET
    :rtype: float
    """

    """ 
    # if it is not possible to schedule this reading after sensor data is collected,
    # uncomment the sleep below
    if is_scheduled():  # do not wait when testing or making forced readings
        utime.sleep(60)  # wait 1 min for sensor data collection to complete
    """

    fail = False
    lock()  # multi-thread protection

    # we have to have at least a sample from each
    if at_cnt == 0 or rh_cnt == 0 or bp_cnt == 0 or ri_cnt == 0 or ws_cnt == 0:
        # do not have the samples needed to compute
        fail = True
        message = "ET fail due to lack of samples: AT {}, RH {}, BP {}, RI {}, WS {}".format(
            at_cnt, rh_cnt, bp_cnt, ri_cnt, ws_cnt)
    else:
        # we copy current results to local variables
        f_at_avg = at_sum / float(at_cnt)
        f_at_max = at_max
        f_at_min = at_min
        f_rh_max = rh_max
        f_rh_min = rh_min
        f_bp_avg = bp_sum / float(bp_cnt)
        f_ri_avg = ri_sum / float(ri_cnt)

        # Daily wind speed run.  One hour at 5 km/hr = 5km of wind run. The sum of all the hours is the daily wind run.
        # We expect to have 24 readings.  If not, we will compensate as the equation needs a daily wind run.
        if is_scheduled():
            f_ws_run = (ws_sum/float(ws_cnt)) * 24.0
        else:  # not scheduled - forced reading or system in test
            f_ws_run = ws_sum

        message = "AT samples {}, avg {}, min {}, max {} {}\n" \
                  "RH samples {}, min {}, max {} %\n" \
                  "BP samples {}, avg {} {}\n" \
                  "RI samples {}, avg {} {}\n" \
                  "WS samples {}, run {} {} day".format(
                    at_cnt, f_at_avg, f_at_min, f_at_max, units_AT,
                    rh_cnt, rh_min, rh_max,
                    bp_cnt, f_bp_avg, units_BP,
                    ri_cnt, f_ri_avg, units_RI,
                    ws_cnt, f_ws_run, units_WS)

        # reset running tallies if this is a scheduled reading
        # or if recording is stopped
        if is_scheduled() or (setup_read("Recording").upper() == "OFF"):
            reset_ET()

    unlock()

    # after unlocking, print the message for diagnostics
    if print_results:
        print(message)

    if fail:
        # do not proceed with computation
        raise ValueError(message)
    else:
        # Convert units from sensor reading to units needed in computation

        if units_AT == 'F':
            f_at_avg = (f_at_avg - 32.0) / 1.8
            f_at_min = (f_at_min - 32.0) / 1.8
            f_at_max = (f_at_max - 32.0) / 1.8
        # else use 'C'

        # limit check (-50C to +50C)
        if f_at_avg > 50.0: f_at_avg = 50.0
        if f_at_min > 50.0: f_at_min = 50.0
        if f_at_max > 50.0: f_at_max = 50.0
        if f_at_avg < -50.0: f_at_avg = -50.0
        if f_at_min < -50.0: f_at_min = -50.0
        if f_at_max < -50.0: f_at_max = -50.0

        if units_BP == 'Hg':
            f_bp_avg = f_bp_avg * 33.864
        # else use 'mb'

        if units_RI == 'Lyh':
            f_ri_avg = f_ri_avg * 24.0
        elif units_RI == 'Lym':
            f_ri_avg = f_ri_avg * (24.0 * 60.0)
        elif units_RI == 'Wm2':
            f_ri_avg = f_ri_avg * 2.06363
        # else use 'Lyd':

        if units_WS == 'mph':
            f_ws_run = f_ws_run * 1.609344
        elif units_WS == 'mps':
            f_ws_run = f_ws_run * 3.6
        elif units_WS == 'kn':
            f_ws_run = f_ws_run * 1.852
        elif units_WS == 'fps':
            f_ws_run = f_ws_run * 1.09728
        # else use 'kph':

        # Determine albedo
        albedo = 0.21;
        if output_ET == 'ETWater':
            albedo = 0.06;

        at_median = (f_at_max + f_at_min) / 2.0  # Average temperature as used in formula

        ap_max = 7.5 * f_at_max / (f_at_max + 237.3)
        ap_min = 7.5 * f_at_min / (f_at_min + 237.3)

        svpmi = 6.108 * pow(10.0, ap_min)
        svpma = 6.108 * pow(10.0, ap_max)

        # Pressure at mean temp
        vpsl = 0.5 * (svpmi + svpma)

        # Minimum air vapor pressure
        avpmi = svpmi * 0.01 * f_rh_min

        # Maximum air vapor pressure
        avpma = svpma * 0.01 * f_rh_max

        # Pressure at mean temperature
        vpal = 0.5 * (avpmi + avpma)

        # Latent heat of vaporization
        hl = 595.0 - 0.51 * at_median

        # Net radiation
        net_rad = 0.95 * (1.0 - albedo) * f_ri_avg - 64.0

        # Saturated vapor pressure curve
        delta = 33.8639 * (0.05904 * pow((0.00739 * at_median + 0.8072), 7.0) - 0.0000342)

        # Psychrometric constant
        gamma = 0.242 * f_bp_avg / (0.622 * hl)

        # Adjust for height above ground - using standard log wind profile
        factor = pow(2.0 / wind_elevation, 0.2)
        f_ws_run = f_ws_run * factor

        # convert wind from km/day to m/s
        new_wind = f_ws_run * 0.01157407

        # Evaporation from surface of well watered short grass (old ASCE calculation).
        ea = 15.36 * (1.0 + 0.0062 * f_ws_run) * (vpsl - vpal)

        intermed_val1 = delta / (delta + gamma) * net_rad
        intermed_val2 = gamma / (delta + gamma) * ea
        et0 = (intermed_val1 + intermed_val2) / hl

        # New ASCE formula. First, define the numerator and denominator constants cn, cd
        if output_ET == 'ETo':
            cn = 900.0
            cd = 0.34
        elif output_ET == 'ETr':
            cn = 1600.0
            cd = 0.38
        elif output_ET == 'ETWater':
            cn = 900.0
            cd = 0.34
        else:
            raise ValueError("ET output not valid: " + output_ET)

        # Convert Delta and Gamma to kPa/deg.C
        new_delta = 0.1 * delta
        new_gamma = 0.1 * gamma

        # Convert the net radiation to megajoules/sq. meter/day 0.041858 is the conv. factor
        new_solar = net_rad * 0.041858

        # vpsl and vpal are the vapor pressures -- need conversion to kPa
        es = vpsl * 0.1
        ea = vpal * 0.1

        # Apply equation in several parts:
        # First part - 0.408 * Delta * (Rn - G) - noting that G is normally taken as zero
        p1 = 0.408 * new_delta * new_solar
        # Second part - u2 * (es - ea)
        p2 = new_wind * (es - ea)
        # Third Part - Gamma * Cn /(T + 273)
        p3 = new_gamma * cn / (f_at_avg + 273)
        # Denominator - Delta + Gamma * (1 + Cd * u2)
        denom = new_delta + new_gamma * (1.0 + cd * new_wind)

        et0 = (p1 + p3 * p2) / denom  # this is in mm

        if et0 < 0.0:
            et0 = 0.0

        # read units from setup
        if not is_being_tested():  # tests do not have proper setups
            global units_ET
            units_ET = setup_read("M{} Units".format(index()))

        # Convert the units if required
        if units_ET == 'in':
            result_ET = et0 / 25.4
        elif units_ET == 'cm':
            result_ET = 0.1 * et0
        else:  # use 'mm':
            result_ET = et0

        if print_results:
            print("ET {} {}".format(result_ET, units_ET))
        return result_ET


def test_ET():
    """Unit test routine"""
    global units_AT
    global units_BP
    global units_WS
    global units_RI
    global units_ET
    global output_ET
    global wind_elevation
    global print_results

    # run tests quietly.  let asserts notify on failure
    print_results = False

    # set to units used in testing
    units_AT = 'C'
    units_BP = 'mb'
    units_RI = 'Lyd'
    units_WS = 'kph'
    units_ET = 'cm'
    output_ET = 'ETo'
    wind_elevation = 2.0

    """Test runs on a single sample"""
    reset_ET()
    meas_AT(20)
    meas_RH(50)
    meas_BP(1000)
    meas_RI(720)  # 720Lyd ~= 349Wm2
    meas_WS(5)

    et = compute_ET(0)
    assert (abs(0.5604 - et) < 0.001)

    """Test runs on a day's worth of hourly samples"""
    reset_ET()
    for i in range(24):
        meas_AT(20)
        meas_RH(50)
        meas_BP(1000)
        meas_RI(720)
        meas_WS(5)

    et = compute_ET(0)
    assert (abs(0.6219 - et) < 0.001)

    """ Test uses different sensor readings"""
    reset_ET()
    for i in range(18):
        meas_AT(20)
        meas_RH(50)
        meas_BP(1000)
        meas_RI(720)
        meas_WS(5)

    for i in range(6):
        meas_AT(30)
        meas_RH(80)
        meas_BP(1050)
        meas_RI(1200)
        meas_WS(0)

    et = compute_ET(0)
    assert (abs(0.7285 - et) < 0.001)

    """This tests checks different units"""
    reset_ET()

    # set units
    units_AT = 'F'
    units_BP = 'Hg'
    units_RI = 'Wm2'
    units_WS = 'mph'
    units_ET = 'in'
    output_ET = 'ETo'
    wind_elevation = 2.0

    for i in range(24):
        meas_AT(88)
        meas_RH(66)
        meas_BP(28.2)
        meas_RI(2001)
        meas_WS(8.6)

    et = compute_ET(0)
    assert(abs(1.40537 - et) < 0.001)
