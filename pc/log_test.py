from sl3 import *
import utime

""" This module tests out the Log class as well as illustrating its usage."""


def print_test_log(s1, s2="", s3=""):
    """ helps debug log test function """
    # uncomment to print log test
    # print(s1, s2, s3)


def test_log_a1():
    """ write and read log entries """
    # this is the interval we log at
    interval = sl3_hms_to_seconds("00:15:00")

    # this is our base time
    time_base = utime.time() - interval * 6.0

    # we use these for the logged value
    value_base = 0.0
    value_change = 1.1

    # create several readings
    time_runner = time_base
    value_runner = value_base
    print_test_log('\r\nwriting:')
    for i in range(0, 5):
        time_runner += interval
        value_runner += value_change
        r = Reading(time=time_runner, label="TL_1", value=value_runner,
                    units="ft", quality="G", right_digits=2, etype="M")
        r.write_log()
        print_test_log('wrote ', r)
        # create a second, confounding reading with the same time but diff label
        rc = r
        rc.label = "FISH"
        rc.write_log()
        print_test_log('wrote ', rc)

    # read back from the log, starting with the most recent
    print_test_log('\r\nread back from newest:')
    l = Log(match="TL_1", pos=LOG_NEWEST)
    for i in range(0, 5):
        r = l.get_older()
        print_test_log('read  ', r)
        assert (r.label == "TL_1")
        assert (r.value == value_runner)
        assert (r.time == time_runner)
        assert (r.units == "ft")
        assert (r.quality == "G")
        assert (r.etype == "M")
        assert (r.time == time_runner)
        value_runner -= value_change
        time_runner -= interval

    # read back from the log, starting with least recent
    print_test_log('\r\nread back from oldest:')
    l = Log(match="TL_1", pos=LOG_OLDEST)
    for i in range(0, 5):
        r = l.get_newer()
        print_test_log('read  ', r)
        value_runner += value_change
        time_runner += interval
        assert (r.label == "TL_1")
        assert (r.value == value_runner)
        assert (r.time == time_runner)
        assert (r.units == "ft")
        assert (r.quality == "G")
        assert (r.etype == "M")
        assert (r.time == time_runner)

    # read back from the log using the count
    print_test_log('\r\nread back counting from newest:')
    l = Log(match="TL_1", pos=LOG_NEWEST, count=5)
    verify_count = 0
    for r in l:
        print_test_log('read  ', r)
        verify_count += 1
        assert (r.label == "TL_1")

    assert (verify_count == 5)

    # read back from the log using the count
    print_test_log('\r\nread back counting:')
    l = Log(match="TL_1", pos=LOG_OLDEST, count=5)
    verify_count = 0
    for r in l:
        print_test_log('read  ', r)
        verify_count += 1
        assert (r.label == "TL_1")

    assert (verify_count == 5)

    # read back both TL_1 and FISHY
    print_test_log('\r\nread back counting with FISHY too:')
    l = Log(pos=LOG_NEWEST, count=10)
    verify_count = 0
    for r in l:
        print_test_log('read  ', r)
        verify_count += 1
        assert (r.label == "TL_1" or r.label == "FISH")

    assert (verify_count == 10)
