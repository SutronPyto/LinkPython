""" This is the main file for PC python development.  
Call the functions you would like to test form here."""

from sl3 import *
import utime
import sdi12
import log_test
import event_based_logging
import insat_test
import gps_tracker
import auto_sampler_eight_triggers
import general_purpose


def print_header():
    print("module", __name__, "running at", end=" ")
    print(ascii_time(utime.localtime()))


def test_log_sim():
    """Does a quick test of reading the simulated log"""
    count = 0
    time_base = 0
    for reading in Log(match="stage", pos=LOG_OLDEST):
        assert (reading.label == "stage")
        assert (reading.time > time_base)
        time_base = reading.time
        count += 1

    assert (count == 3)


def test_wait_for():
    from io import StringIO
    s = StringIO('this is a test message !!!\r\nthis is only a test\r\n')
    assert (wait_for(s, 'is'))
    assert (s.tell() == 4)
    assert (wait_for(s, 'i*a '))
    assert (s.tell() == 10)
    assert (wait_for(s, 'me???ge '))
    assert (s.tell() == 23)
    assert (wait_for(s, '^M^J'))
    assert (s.tell() == 28)


def test_bin6():
    assert (bin6(10.0, 1) == b"J")
    assert (bin6(1.0, 2) == b"@A")
    assert (bin6(12345.0) == b"C@y")
    assert (bin6(-12345.0) == b"|?G")
    assert (bin6(12.39, 3, 2) == b"@SW")
    assert (bin6(123.9, 3, 1) == b"@SW")
    assert (bin6(1239.0) == b"@SW")
    assert (bin6(-0.29, 3, 2) == b"??c")
    assert (bin6(-0.28, 3, 2) == b"??d")
    assert (bin6(-0.10, 3, 2) == b"??v")


def test_bin_to_str():
    assert (bin_to_str(1094861636, 4) == b'ABCD')
    assert (bin_to_str(1094861636, -4) == b'DCBA')
    assert (bin_to_str(126, 1) == b'~')
    assert (bin_to_str(125.6, 1) == b'~')
    assert (bin_to_str(4.9, 4) == b'@\x9c\xcc\xcd')
    assert (bin_to_str(4.9, -4) == b'\xcd\xcc\x9c@')
    assert (bin_to_str(6.7, 8) == b'@\x1a\xcc\xcc\xcc\xcc\xcc\xcd')


def test_bit_convert():
    assert (bit_convert(b'DCBA', 1) == 1094861636)
    assert (bit_convert(b'ABCD', 2) == 1094861636)
    assert (bit_convert(b'@\x9c\xcc\xcd', 4) == 4.900000095367432)
    assert (bit_convert(b'\xcd\xcc\x9c@', 3) == 4.900000095367432)
    assert (bit_convert(b'@\x1a\xcc\xcc\xcc\xcc\xcc\xcd', 6) == 6.7)


def test_sdi12():
    assert (sdi12.sdi_send_command_get_reply("0M!") == "00007")
    assert (sdi12.sdi_send_command_get_reply("bla bla") == "No reply")
    assert (sdi12.sdi_collect(0)[0] == 1.1111)
    assert (sdi12.sdi_collect(0)[1] == -2.222)
    assert (sdi12.sdi_collect(0)[2] == 3.33)
    assert (sdi12.sdi_collect(0)[3] == 4.4)
    assert (sdi12.sdi_collect(0)[4] == 5)
    assert (sdi12.sdi_collect(0)[5] == -2.5e-45)
    assert (sdi12.sdi_collect(0)[6] == 43.56E+4)
    assert (sdi12.sdi_collect(0, 'X')[0] == 1.1111)
    assert (sdi12.sdi_collect_improved(0, 0, 'X') == 1.1111)
    assert (sdi12.sdi_collect_improved(0, 1, 'X') == -2.222)



def test_dga():
    import dga
    assert (dga.dga_format("\r\n05/12/2017,15:18:00,Temp,26.00,,G\r\n05/12/2017,15:18:00,Batt,12.51,,G\r\n\r\n") ==
            "SELFTIMED ON UNIT: Sutron Satlink 3 DATE: 05/12/2017 TIME: 15:18:00 Temp 26.00 G OK  Batt 12.51 G OK  ")
    assert (dga.dga_format("\r\n05/12/2017,17:34:00,Temp,MISSING\r\n05/12/2017,15:18:00,Batt,12.51,,G\r\n\r\n") ==
            "SELFTIMED ON UNIT: Sutron Satlink 3 DATE: 05/12/2017 TIME: 17:34:00 Temp MISSING OK  Batt 12.51 G OK  ")
    assert (dga.dga_format(
        "This is a test") == "SELFTIMED ON UNIT: Sutron Satlink 3 DATE: 05/12/2017 TIME: 15:18:00 Temp 26.00 G OK  Batt 12.51 G OK  ")


def test_sim():
    assert (batt() > 0)
    assert (batt() < 20)
    assert (is_being_tested() == True)


def test_crc():
    b = '123456789'
    assert (crc_ssp(b) == 0xbb3d)
    assert (crc_modbus(b) == 0x4b37)
    assert (crc_xmodem(b) == 0x31c3)
    assert (crc_kermit(b) == 0x8921)
    assert (crc_dnp(b) == 0x82ea)
    assert (crc(b, 0x1021) == 0x31c3)
    assert (crc_kermit(b'123456789') == 0x8921)


def test_setup():
    assert (setup_read("Station Name") == "Sutron Satlink 3")
    assert (setup_write("Station Name", "Test") is None)
    assert (setup_write("m9 slope", "1.23") is None)
    assert (setup_write("m9 slope", 4.56) is None)
    assert (setup_write("m9 slope", 789) is None)
    try:
        setup_write("m9 slope", "TEST")
        assert (0)
    except SetupError:
        pass


def test_daylight():
    import daylight
    assert (daylight.minutes_of_daylight(5) == 1.0)
    assert (daylight.minutes_of_daylight(5) == 2.0)


def test_meas_simple():
    import meas_simple
    assert (meas_simple.twelve_more(3) == 15)


def test_parity():
    import parity
    assert (parity.even(b'test') == b'te\xf3t')
    assert (parity.odd(b'test') == b'\xf4\xe5s\xf4')


def test_txformat_simple():
    import txformat_simple
    assert (txformat_simple.append_info("test") == "test Little Creek A21938")
    assert (txformat_simple.prefix_id_1("test") == "A17_BS_128 test")
    assert (txformat_simple.prefix_id_2("test") == "Sutron Satlink 3 test")
    assert (txformat_simple.destroy("test") == "kittens ate your data")


def test_sgn():
    assert (sgn(-12) == -1)
    assert (sgn(-1) == -1)
    assert (sgn(0) == 0)
    assert (sgn(1) == 1)
    assert (sgn(33) == 1)


def test_reset_count():
    reset_string_a1 = "Power reset counter 1"
    reset_string_a2 = "Watchdog reset counter 38\r\n"
    reset_string_a3 = "Power reset counter 2\r\nSoftware reset counter 11\r\n"
    reset_string_a4 = "Power reset counter 1\r\nnFault reset counter 2009\r\nSoftware reset counter 7123"
    from sl3 import _reset_count_parse
    assert (_reset_count_parse(reset_string_a1) == 1)
    assert (_reset_count_parse(reset_string_a2) == 38)
    assert (_reset_count_parse(reset_string_a3) == 13)
    assert (_reset_count_parse(reset_string_a4) == 1 + 2009 + 7123)


ver_str_a1 = '''Sutron Satlink 3 Logger V2 Debug Version 8.10 Build 10:28:00 07/21/2017 revision 2578
PIC     7.11
GPS     u-blox 1.00 (59842), 00070000
WiFi    1.00
SL3 S/N 19XY892, Micro 0, Tx 0
Cell    P/N CELLULAR-MOD-1, S/N 1234, rev -, port 1
PREF    P/N DEV_ONE, S/N fcc23d031ba9, rev -, port 2
Radios Installed: Environmental Satellite, Cell
'''

ver_boot_str_a1 = '''Sutron Satlink 3 Logger V2 Version 8.10 Build  8:47:57 06/21/2017 re
Radios Installed: Environmental Satellite, Cell'''


def test_ver():
    from sl3 import _ver_parse
    assert (_ver_parse(ver_str_a1) == [8, 10, 2578])
    assert (_ver_parse(ver_boot_str_a1) == [8, 10, 0])


def test_log_task_trigger():
    from log_task_trigger import _log_task_trigger
    assert (_log_task_trigger("S1 Boot") == None)


def test_meas_find():
    global sutron_link
    if sutron_link:  # if running on Satlink, change setup first
        setup_write("M1 LABEL", "RH")
        setup_write("M2 LABEL", "AT")
        setup_write("M3 LABEL", "DP")
    assert (meas_find_index("RH") == 1)
    assert (meas_find_index("AT") == 2)
    assert (meas_find_index("DP") == 3)
    assert (meas_find_label(1) == "RH")
    assert (meas_find_label(2) == "AT")
    assert (meas_find_label(3) == "DP")


def test_sl3_hms_to_seconds():
    assert (sl3_hms_to_seconds("00:00:00") == 0)
    assert (sl3_hms_to_seconds("00:00:01") == 1)
    assert (sl3_hms_to_seconds("00:01:00") == 60)
    assert (sl3_hms_to_seconds("00:01:19") == 79)
    assert (sl3_hms_to_seconds("10:01:19") == 3600*10+79)
    assert (sl3_hms_to_seconds("01:01:01") == 3600+60+1)
    assert (sl3_hms_to_seconds("24:00:00") == 86400)


def test_rating_table():
    from rating_table import rating_table
    assert (rating_table(-.5) == 0)
    assert (rating_table(.5) == 2.5)
    assert (rating_table(5) == 42)
    assert (rating_table(73) == 41287.0)
    assert (rating_table(73.05) == -99.99)


def test_prev_logged_value():
    # get a previously logged value that we expect to find in the log
    r = event_based_logging.prev_logged_value(4);
    assert(r.label == 'stage')
    assert(r.value == 4.72)
    assert(r.quality == 'G')

    # we do not expect to find a previously logged value of M31
    r = event_based_logging.prev_logged_value(31);
    assert(r.quality == 'B')


def run_tests():
    assert (bytes_to_str(b'Test\xb0\xfe\xff') == str(b'Test\xb0\xfe\xff', 'latin1'))
    assert (str_to_bytes('Test\xb0\xfe\xff') == bytes('Test\xb0\xfe\xff', 'latin1'))
    test_log_sim()
    test_wait_for()
    test_bin6()
    test_sdi12()
    test_dga()
    test_crc()
    test_setup()
    test_daylight()
    test_meas_simple()
    test_bin_to_str()
    test_bit_convert()
    test_parity()
    test_txformat_simple()
    test_sgn()
    test_reset_count()
    test_ver()
    test_log_task_trigger()
    test_meas_find()
    test_sl3_hms_to_seconds()
    log_test.test_log_a1()
    test_rating_table()
    test_prev_logged_value()
    insat_test.test_insat_all()
    gps_tracker.test_gps_read_position()
    auto_sampler_eight_triggers.auto_eight_test()
    general_purpose.gp_test()

    print("All tests complete.")


""" main body of code """
print_header()
run_tests()
