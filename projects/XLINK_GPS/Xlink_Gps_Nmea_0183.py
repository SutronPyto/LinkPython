""" XLink script that reads positional information from a GPS module on the serial port
The GPS module needs to provide output in NMEA 0183 format
Script parses GPGGA sentance from GPS for latitude and longitude

if GPS outputs this:
    "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
lattitude is 4807.038  in DDMM.MMMM format.
longitude is 1131.0    in DDDMM.MMMM format
South and west produce negative numbers

A script task needs to be setup and linked to function capture_gps_info
The task will listen to data from GPS and update the globals m_latitude and m_longitude

Position may be logged (and included in tranmissions) by setting up
two measurements to meas_latitude and meas_longitude functions
Schedule the measurements to start several minutes after the script task

Position may be viewed in the script status

Position may be appended to the tarnsmission data via function append_lat_long
"""

from sl3 import *
import serial
import utime

# globals hold last read position
m_valid = False  # do we have valid data?
m_invalid = -999.9  # what value to provide when lat/long is unknown
m_latitude = m_invalid
m_longitude = m_invalid
m_time_last = 0
m_last_line = ""  # last sentance from gps
m_last_capture = []  # last capture session


def update_globals(valid, lat, long, sentance):
    """
    updates the global variables with gps data
    """
    global m_valid, m_latitude, m_longitude, m_last_line, m_time_last, m_invalid, m_last_capture

    m_valid = valid
    if valid:
        m_latitude = lat
        m_longitude = long
    else:
        m_latitude = m_invalid
        m_longitude = m_invalid

    m_last_line = sentance
    if sentance:
        m_last_capture.append(sentance)

    m_time_last = utime.time()


def print_results():
    """ prints results from the global variables"""
    global m_valid, m_latitude, m_longitude, m_last_line, m_time_last, m_invalid, m_last_capture

    if m_valid:
        print("Lat {:.{}f}, Long {:.{}f}, captured at {}.  Last sentance:".format(m_latitude, 4, m_longitude, 4,
                                                                                  ascii_time(utime.localtime())))
        print(m_last_line)
    elif m_last_line:
        print("No lat/long info.  Last capture was at {}.  Last sentance:".format(ascii_time(m_time_last)))
        print(m_last_line)
    else:
        print("No valid data from GPS.  Last attempt was at {}".format(ascii_time(m_time_last)))

    print("Last capture:")
    print(m_last_capture)
    print()


def nmea_check_crc(sentence):
    """ checks NMEA sentance for a valid CRC"""
    # Remove any leading or trailing whitespace and the $ and * characters
    sentence = sentence.strip("$").strip("\r\n")
    # Split the sentence: data content is after $ and to *, CRCis after *
    fields = sentence.split("*")

    if len(fields) < 2:
        return False
    else:
        # Calculate the XOR checksum of the sentence
        calculated_crc = 0
        for c in fields[0]:
            calculated_crc ^= ord(c)

        # parse the CRC from the string as hex
        expected_crc = int(fields[1], 16)

        # Return True if the calculated CRC matches the expected CRC, False otherwise
        if calculated_crc == expected_crc:
            return True
        else:
            return False


def parse_nmea_0183_for_position(sentance):
    """
    parses provided sentance for NMEA 0183 GNSS/GPS info
    "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
    if there is valid (non-zero) position info, it returns True
    along with latitude and longitude w/o conversions
    example above would return True, 4807.038, 1131.0
    :param sentance: string
    :return: Bool Valid, float latitude, float longitude
    """
    if len(sentance):
        if sentance[0] == '$':
            if nmea_check_crc(sentance):
                tokens = sentance.split(',')
                if tokens[0] == "$GPGGA":
                    lat = float(tokens[2])
                    if tokens[3] == 'S':  # denote south as negative
                        lat = -lat
                    long = float(tokens[4])
                    if tokens[5] == 'W':  # West is negative
                        long = -long
                    return True, lat, long

    return False, 0.0, 0.0


def parse_data_update_globals(sentance):
    valid, lat, long = parse_nmea_0183_for_position(sentance)
    update_globals(valid, lat, long, sentance)
    return valid


def gps_serial_port():
    """ captures data from the GPS on the RS232 port
    captured data is parsed for location
    returns true if valid location is found"""

    total_time_sec = 30 * 60  # how much total time the GPS has to find lat/long
    baud_rate = 9600

    global m_last_capture
    m_last_capture.clear()

    port_gps = serial.Serial()  # serial port object.
    port_gps.port = "RS232"
    port_gps.baudrate = baud_rate
    port_gps.bytesize = 8
    port_gps.parity = 'N'
    port_gps.stopbits = 1
    port_gps.rtscts = False
    port_gps.dsrdtr = False
    port_gps.xonxoff = False
    port_gps.timeout = total_time_sec
    port_gps.inter_byte_timeout = 5
    port_gps.open()
    port_gps.flush()

    start_time = utime.time()
    while True:
        raw_data = port_gps.readline()
        sentance = raw_data.decode()  # decode from binary to unicode str

        if parse_data_update_globals(sentance):
            break

        if (utime.time() - start_time) > total_time_sec:
            update_globals(False, 0, 0, "Timed out")
            break

    port_gps.close()


@TASK
def capture_gps_info():
    """ connect his function to a task that runs as often as the gps should be read"""
    if is_being_tested():  # if we are testing, do not grab data from the GPS, but run code on this:
        sentance = "$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76\r\n"
        parse_data_update_globals(sentance)
    else:
        gps_serial_port()

    print_results()


@MEASUREMENT
def meas_latitude(inval):
    """Associate with a measurement to have it log latitude.
    The measurement should be setup as manual entry.

    Please note that this returns a result of m_invalid until
    the task gps_keep_on_and_read_position is run"""
    global m_latitude
    return m_latitude


@MEASUREMENT
def meas_longitude(inval):
    """ Like meas_latitude, but for longitude"""
    global m_longitude
    return m_longitude


@TXFORMAT
def append_lat_long(standard):
    """Appened m_latitude and m_longitude to transmission."""
    global m_latitude, m_longitude
    return "{} latitude= {:.4f}, longitude= {:.4f}".format(standard, m_latitude, m_longitude)


def test_xlink_nmea_0183():
    """ test routine validates crc and parsing """
    global m_valid, m_latitude, m_longitude, m_last_line, m_time_last, m_invalid

    nmea_sentences = [
        '$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76',
        '$GPGSA,A,3,10,07,05,02,29,04,08,13,,,,,1.72,1.03,1.38*0A',
        '$GPGSV,3,1,11,10,63,137,17,07,61,098,15,05,59,290,20,08,54,157,30*70',
        '$GPGSV,3,2,11,02,39,223,19,13,28,070,17,26,23,252,,04,14,186,14*79',
        '$GPGSV,3,3,11,29,09,301,24,16,09,020,,36,,,*76',
        '$GPRMC,092750.000,A,5321.6802,N,00630.3372,W,0.02,31.66,280511,,,A*43',
        '$GPGGA,092751.000,5321.6802,N,00630.3371,W,1,8,1.03,61.7,M,55.3,M,,*75',
        '$GPGSA,A,3,10,07,05,02,29,04,08,13,,,,,1.72,1.03,1.38*0A',
        '$GPGSV,3,1,11,10,63,137,17,07,61,098,15,05,59,290,20,08,54,157,30*70',
        '$GPGSV,3,2,11,02,39,223,16,13,28,070,17,26,23,252,,04,14,186,15*77',
        '$GPGSV,3,3,11,29,09,301,24,16,09,020,,36,,,*76',
        '$GPRMC,092751.000,A,5321.6802,N,00630.3371,W,0.06,31.66,280511,,,A*45'
    ]
    for line in nmea_sentences:
        assert (nmea_check_crc(line))

    sentance = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid)
    assert (m_latitude == 4807.038)
    assert (m_longitude == 1131.0)

    sentance = "$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76\r\n"
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid)
    assert (m_latitude == 5321.6802)
    assert (m_longitude == -630.3372)

    sentance = "$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76\r\n"
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid)
    assert (m_latitude == 5321.6802)
    assert (m_longitude == -630.3372)

    sentance = "1.03,61.7,M,55.2,M,,*76\r\n"
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid == False)

    sentance = "$GPGGA,092750.000,5321.6802,N,00630.3372,W"
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid == False)

    sentance = ""
    parse_data_update_globals(sentance)
    print_results()
    assert (m_valid == False)


global sutron_link
if not sutron_link:  # run tests on PC only
    test_xlink_nmea_0183()
