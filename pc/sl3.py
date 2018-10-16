# This module provides the Application Programming Interface for the Sutron Satlink.
# It consists of functions that provide access to Satlink's systems.

# Note: when you add a function or class to this file, please also add it to the list of functions section of sl3.rst

sutron_link = True  # tracks whether the script is run on the embedded platform

import sys

if 'win' in sys.platform:
    # running on pc
    try:
        sutron_link = False
        from sl3_sim import *
    except ImportError:
        # probably performing a build for documentation
        import re
else:
    # running on Sutron Link
    import re

import utime
import _thread

GLOBAL_LOCK = _thread.allocate_lock()


class SetupError(Exception):
    pass


def lock():
    """
    lock() and unlock() may be used to protect global variables from being corrupted by
    code designed to be run by multiple tasks at the same time. They do this by allowing only
    one task to proceed past the lock() statement at a time. Consider ``Example 1`` where
    a global variable is decremented. Without the lock, two tasks could interfere with each other
    and prevent the global variable from being decremented correctly. Similarly a section of code
    can be protected, such that only one task can enter that code at a time. If you need to protect
    a section of code that's more substantial than some quick operations, consider using
    _thread.allocate_lock() to create a unique lock variable instead, and reserve lock()/unlock()
    for the quick sections.

    Example 1 - Simple lock/unlock::

        from sl3 import lock, unlock
        global my_global
        lock()
        my_global = my_global - 1
        unlock()
            
    Example 2 - Exception safe lock/unlock::

        from sl3 import lock, unlock
        # use try-finally to make sure the global lock is always released
        # even if an exception occurs:
        try:
            lock()
            call_my_function()
        finally:
            unlock()
            
    Example 3 - Exception safe using GLOBAL_LOCK::

        # try-finally is a little cumbersome, here's a simpler way to protect a section of code
        # in an exception-safe way:
        from sl3 import GLOBAL_LOCK
        with GLOBAL_LOCK:
            call_my_function()
            
    Example 4 - Custom lock::

        # in cases where long sections of code must be protected, it's possible to introduce 
        # custom locks to avoid holding up code which use lock()/unlock():
        import _thread
        MY_LOCK = _thread.allocate_lock()
        #
        @MEASUREMENT
        def shared_measurement(num):
            with MY_LOCK:
                return my_function(num)
    """
    global GLOBAL_LOCK
    GLOBAL_LOCK.acquire()


def unlock():
    """
    lock() and unlock() are typically used together to protect global variables.
    """
    global GLOBAL_LOCK
    GLOBAL_LOCK.release()


def get_api_version():
    """
    The version of the API.

    :return: API version
    :rtype: float
    """
    return 0.1


def index():
    """
    Returns the index of the calling measurement or transmission or script task. 
    For example, if a script hooked into measurement M7 were to call this function, it would return 7.
    If not called from a meas/tx/task, routine returns 1.

    :return: index of caller
    :rtype: int
    """
    return more_info()[0]


def is_scheduled():
    """
    Tells you whether the calling measurement/transmission/script task was scheduled.

    :return: True if scheduled.s
    :rtype: bool
    """
    return more_info()[1]


def time_scheduled():
    """
    Returns the time the calling measurement or transmission or script task was scheduled to run.

    :return: time in seconds since 1970, just like utime.time()
    :rtype: float
    """
    return more_info()[2]


def is_being_tested():
    """
    Tells you whether the function is being called as a part of a test operation.
     
    :return:  If a Python function is being tested by the customer, the value is True.  If the function was invoked by Satlink as a part of normal operation, the value is False.
    :rtype: bool
    """
    return more_info()[3]


def is_clock_updated():
    """
    For Satlink environmental satellite transmissions only, this value is true if the clock
    has been updated since the last transmission.
    May only be used by custom formatting TXFORMAT routines

    :return:  True if there has been a GPS synce since the previous transmission
    :rtype: bool
    """
    return more_info()[5]


def ascii_time(time_t):
    """
    Converts the provided time into an ASCII string:

        >>> ascii_time(utime.localtime())
        '07/03/2017,21:40:57'

    :param time_t: two options:

        time as a float number of seconds since 1970, just like utime.time()

        time as a tuple, as per utime.localtime()
    :return: the time in MM/DD/YYYY,HH:MM:SS
    :rtype: str
    """

    # if it is not already, convert time to a tuple as per localtime()
    if type(time_t) is float:
        time_t = utime.localtime(time_t)
    return "{:02d}/{:02d}/{:04d},{:02d}:{:02d}:{:02d}".format(time_t[1], time_t[2], time_t[0],
                                                              time_t[3], time_t[4], time_t[5])


def ascii_time_hms(time_t):
    """
    Converts the provided time into an ASCII string HH:MM:SS::

        >>> ascii_time_hms(utime.localtime())
        '21:40:57'

    :param time_t: two options:

        time as a float number of seconds since 1970, just like utime.time()

        time as a tuple, as per utime.localtime()
    :return: the time in HH:MM:SS
    :rtype: str
    """
    if type(time_t) is float:
        time_t = utime.localtime(time_t)
    return "{:02d}:{:02d}:{:02d}".format(time_t[3], time_t[4], time_t[5])


def seconds_since_midnight():
    """returns the number of seconds that have elapsed since midnight as an integer"""
    current_time = utime.localtime()
    sec_elapsed = current_time[3] * 3600  # hour
    sec_elapsed += current_time[4] * 60  # min
    sec_elapsed += current_time[5]  # sec
    return sec_elapsed


def str_to_bytes(s):
    """
    MicroPython does not support the latin1 character set, but this is equivalent to bytes(s, 'latin1')
    which converts bytes to string keeping the bytes exactly as-is without regard to unicode encoding
    """
    return bytes(list(ord(x) for x in s))


def bytes_to_str(b):
    """
    MicroPython does not support the latin1 character set, but this is equivalent to str(s, 'latin1')
    which converts a string to bytes without regard to unicode encoding
    """
    return "".join(map(chr, b))


def sl3_time_to_seconds(str_dt):
    """
    Convert a string to time.
    
    :param str str_dt: SL3 date and time string YYYY/MM/DD HH:MM:SS or HH:MM:SS MM/DD/YYYY
    :return: time in seconds since 1970, just like utime.time()
    :rtype: float
    """
    import re
    # Regular expression helper: https://regex101.com/
    # Find date in string with date pattern, split and assign to variables.
    yyyy, mm, dd = re.search(r"\d+/\d+/\d+", str_dt).group(0).split("/")

    if len(dd) == 4:
        # This is a log entry and date order is MM/DD/YYYY format instead of YYYY/MM/DD
        yyyy, mm, dd = dd, yyyy, mm

    hh, min, ss = re.search(r"\d+:\d+:\d+", str_dt).group(0).split(":")

    return utime.mktime((int(yyyy), int(mm), int(dd), int(hh), int(min), int(ss), 0, 0, 0))


def sl3_hms_to_seconds(str_hms):
    """
    Convert a HH:MM:SS string to a number of seconds.

    :param str str_hms: time string HH:MM:SS
    :return: time in seconds
    :rtype: int
    """
    import re
    # Regular expression helper: https://regex101.com/
    # Find time in string with time pattern, split and assign to variables.
    hh, min, ss = re.search(r"\d+:\d+:\d+", str_hms).group(0).split(":")

    return int(hh)*3600 + int(min)*60 + int(ss)


def meas_as_index(meas_index_or_label):
    """
    Routine converts provided parameter to a measurement index as an integer

    :param meas_index_or_label: either the index or the label of the meas.   1 or 'Sense1'
    :type meas_index_or_label: int or string
    :return: measurement index
    :rtype: int
    """
    if isinstance(meas_index_or_label, str):
        index_as_int = meas_find_index(meas_index_or_label)
    else:
        index_as_int = meas_index_or_label

    return index_as_int


# constants used for the measure routine
READING_LAST, READING_LAST_SCHED, READING_MEAS_SYNC, READING_MEAS_FORCE = 0, 1, 2, 3


def measure(meas_identifier, meas_action=READING_MEAS_SYNC):
    """
    Used to access sensor results via Measurements.  Requires that the measurement be setup.
    Usage examples::

        >>> measure(2)
        08/03/1987,19:42:56,AT,28.5,C,G
        >>> measure(2).value
        28.5
        >>> measure('AT').value
        28.5

        >>> r2 = measure(2)
        >>> r2.value
        28.0
        >>> r2.value += 5
        >>> r2.value
        33.0
        >>> r2.write_log()
        >>> Log().get_newest()
        08/03/1987,19:45:58,AT,33.0,C,G
    
    :param meas_identifier:
        either the measurement index as an int, or the meas label as a str

        index is 1 based, e.g. 4 for M4.

        the label is the customer set label for the meas, e.g. "Sense01" or "AT"

    :param meas_action:
        One of the available constants indicating what action to take.  Options:
            :const: READING_LAST The reading produced when measurement was last made.  Does not start a new measurement.
            :const: READING_LAST_SCHED Like last, but returns the last scheduled (as opposed to live/forced reading).
            :const: READING_MEAS_SYNC  Picks up the last reading synchronized to the schedule.  Avoids extraneous readings.
                If the caller is scheduled for 12:15, this will use the measurement reading made at 12:15, waiting if need be.
                If system is not running, it will make a new measurement
            :const: READING_MEAS_FORCE Initiates a new measurement every time
    :return: The result of the sensor measurements
    :rtype: Reading
    """
    return Reading(c_measure(meas_as_index(meas_identifier), meas_action))


def meas_do_not_log():
    """
    Only usable by @MEASUREMENT scripts.
    Once script returns, the measurement reading will NOT be logged, no matter
    the measurement setup.
    Please note this happens once script returns, not when this function is called.
    """
    return_info(0);


def meas_log_this():
    """
    Only usable by @MEASUREMENT scripts.
    Once script returns, the measurement reading will be logged, no matter
    the measurement setup.
    Please note this happens once script returns, not when this function is called.
    """
    return_info(1);


class Serial_number:
    """
    Provies the  serial number of SL3, microboard, and transmitter board.
    Returned values are ASCII strings containig the serial number.
    """

    @classmethod
    def sl3(cls):
        return command_line("serialNo product", 50).strip()

    @classmethod
    def microboard(cls):
        return command_line("serialNo micro", 50).strip()

    @classmethod
    def transmitter(cls):
        return command_line("serialNo tx", 50).strip()


class Reading:
    """ 
    This class is used to represent a log entry and a measurement result.
        * It is used when reading and writing to the log.
        * It is also used when getting the results of a measurement reading.

    Here is a summary of the properties of a Reading and their default values:
    
    ============  =======     ================================================
    Property      Default     Description
    ============  =======     ================================================
    time          0           time is represented in seconds since 1970 as 
                              returned by utime.time()
    label         ""          a name for the reading
    value         0.0         the value of the reading
    units         ""          the units of the reading (up to 3 characters)
    quality       "G"         can be either 'G' for good or 'B' for bad
    right_digits  0           the number of digits to the right of
                              the decimal point to display
    etype         "M"         represents the type of reading:
    
                              - 'M': a measurement
                              
                              - 'E': an event
                              
                              - 'D': a debug message
    ============  =======     ================================================
        
    Notes
       * When a Reading is printed, the full contents are displayed using csv format::
       
             >>> from sl3 import *
             >>> from utime import time
             >>> r = Reading(time(), "stage", 5.2, "ft", "G")
             >>> print(r)
             08/14/2017,23:23:06,stage,5.20,ft,G
       * Readings may be concatenated with strings using the + and += operators::
       
            >>> from sl3 import *
            >>> from utime import time
            >>> output_format = "HEADER: "
            >>> r1 = Reading(value=4.3, quality='G', label='test', time=time())
            >>> output_format += r1
            >>> print(output_format)
            HEADER: 08/14/2017,23:37:43,test,4.30,,G
       * Two Reading's may be compared for equality (or inequality)::
       
             >>> from sl3 import *
             >>> from utime import time
            >>> r1 = Reading(value=4.3, quality='G', label='test', time=time())
            >>> r2 = Reading(value=4.3, quality='G', label='test', time=r1.time)
            >>> r1 == r2
            True
            >>> r1 != r2
            False
    """

    time = 0
    """Time is represented in seconds since 1970 as returned by utime.time()"""

    label = ""
    """A name for the reading; a string up to 11 bytes"""

    value = 0.0
    """The value of the reading, a float"""

    units = ""
    """The units expressed as a string up to three bytes long"""

    quality = "G"
    """A single byte indicating the quailty of the reading, with B indicating a bad value,
    and G indicating a good value"""

    right_digits = 0
    """The number of right digits of the value to show"""

    etype = 'M'
    """
    Represents the type of reading
       * 'M': a measurement
       * 'E': an event
       * 'D': a debug message
    """

    def __init__(self, time=0, label="", value=0.0, units="", quality="G", right_digits=2, etype='M'):
        """
        A Reading can be initialized with another Reading or a tuple, or fields. 
        Here are some examples of differents ways a Reading can be constructed::
        
             from sl3 import *
             from utime import time
             
             # Create a Reading by filling out the fields one by one:
             r = Reading()
             r.time = time()
             r.value = -9.7
             r.label = "at"
             r.quality = 'G'
             r.right_digits = 1
             r.units = 'C' 
             
             # Create a Reading by passing one or more of time, label, value, units, quality, right_digits,
             # and entry type:
             r = Reading(time(), "stage", 5.2, "ft", "G")
             
             # Create a Reading by passing keyword arguments (order doesn't matter):
             r = Reading(value=4.3, quality='G', label='test', time=time())
             
             # Create a Reading by passing another reading:
             r2 = Reading(r)
             
             # Create a Reading by passing a tuple containing the properties
             r = Reading((time(), "stage", 5.2, "ft", "G", 2, 'M'))
        """
        raw = time
        if isinstance(raw, self.__class__):
            self.time, self.label, self.value, self.units = raw.time, raw.label, raw.value, raw.units
            self.quality, self.right_digits, self.etype = raw.quality, raw.right_digits, raw.etype
        elif type(raw) == tuple:
            self.__convert_from_tuple(raw)
        else:
            self.time, self.label, self.value, self.units = time, label, value, units
            self.quality, self.right_digits, self.etype = quality, right_digits, etype

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.time == other.time
                    and self.label == other.label
                    and self.value == other.value
                    and self.units == other.units
                    and self.quality == other.quality
                    and self.right_digits == other.right_digits)
        else:
            raise NotImplementedError

    def asctime(self):
        """
        Converts the time of the Reading into an ASCII string
        :return: the time in MM/DD/YYYY,HH:MM:SS 
        :rtype: str
        """
        t = utime.localtime(self.time)
        return "{:02d}/{:02d}/{:04d},{:02d}:{:02d}:{:02d}".format(t[1], t[2], t[0], t[3], t[4], t[5])

    def __repr__(self):
        return "{},{},{:.{}f},{},{}".format(self.asctime(), self.label, self.value, self.right_digits,
                                            self.units, self.quality)

    def __convert_from_tuple(self, raw):
        self.time, self.label, self.value, self.units, self.quality, self.right_digits, self.etype = raw

    def __convert_to_tuple(self):
        return (self.time, self.label, self.value, self.units, self.quality, self.right_digits, self.etype)

    def write_log(reading):
        """
        Writes the reading to the log::
   
            reading = Reading(value=4.3, quality='G', label='test', time=time())
            reading.write_log()
        """
        write_log_entry(reading.__convert_to_tuple())
        
    def __add__(self, other):
        return str(self) + str(other)

    def __radd__(self, other):
        return str(other) + str(self)

# constants used for specifying a start position in the log
LOG_CURRENT, LOG_NEWEST, LOG_OLDEST = None, 1, 2

class Log:
    """ 
    The Log class is used to access the log.
    It may be used to search the log, matching a log entry label. The search may be bound
    by specifiying an oldest and/or a newest time.

    To access any of the log methods you must create an instance of the Log class::
     
        >>> from sl3 import *
        >>> l = Log()
        >>> l.get_oldest()
        04/04/2017,18:01:43,RS232 Connected,0,,G
        >>> l.get_newer()
        04/04/2017,18:01:43,Reset Soft,278,,G
        >>> l.get_newer()
        04/04/2017,18:01:44,Usb Drive Connected,0,,G
         
    Notes:
        
    - most Log functions return an instance of the Reading class
    - the current position in the log is tracked on a per thread basis to prevent conflicts
    - it's recommended to avoid creating a Log() instance in a global variable to avoid 
      potential conflict with other threads.

      
    Matching by label and time
        If you want to match certain labels, you can pass it in as the match property; 
        an oldest time or a newest time can be specified as well.
        
        Retrieve the most recent Soft Reset event::
        
            >>> from sl3 import Log
            >>> Log(match='Reset Soft').get_newest()
            05/09/2017,15:06:54,Reset Soft,115,,G
            
        Retrieve the last Soft Reset event that occurred yesterday::
        
            >>> t = localtime()
            >>> # localtime() returns the current time in a tuple which is not-modifiable, but we can
            >>> # convert it into a list and create a unique copy with the list() function:
            >>> t1 = list(t)
            >>> # subtract 1 from the day, and set the HH:MM:SS to 00:00:00
            >>> t1[2:6] = (t1[2] - 1, 00, 00, 00)
            >>> # use the list() function to make another unique copy of the current time:
            >>> t2 = list(t)
            >>> # subtract 1 from the day, and set the HH:MM:SS to 23:59:59
            >>> t2[2:6] = (t2[2] - 1, 23, 59, 59)
            >>> # create a Log() instance with the label we wish to match and the oldest time and newest 
            >>> # time and call get__newest() to start searching for a match moving  backwards in time:
            >>> Log(match='Reset Soft', oldest=mktime(t1), newest=mktime(t2)).get_newest()
            05/08/2017,22:21:16,Reset Soft,115,,G
            
        Retrieve the next earlier matching Soft Reset event::

            >>> Log(match='Reset Soft', oldest=mktime(t1), newest=mktime(t2), pos=LOG_CURRENT).get_older()
            05/08/2017,22:19:58,Reset Soft,114,,G
            
        Or to be more efficient we can copy the Log() instance into a variable and then 
        just re-use it::

            >>> log = Log(match='Reset Soft', oldest=mktime(t1), newest=mktime(t2))
            >>> log.get_older()
            5/08/2017,22:11:54,Reset Soft,113,,G
            >>> log.get_older()
            05/08/2017,17:59:44,Reset Soft,112,,G
        
    Iterating with the Log Class
        If we want to manipulate a block of Log entries in Python, we can take advantage of the fact that 
        the Log() class supports iteration. That means we can loop on it. Here's an example
        that displays the last 2 soft resets that have occured::

            >>> from sl3 import Log
            >>> for reading in Log(2, "Reset Soft"):
            ...     print(reading)
            05/08/2017,22:21:16,Reset Soft,115,,G
            05/08/2017,22:19:58,Reset Soft,114,,G
            
       It's also possible to use a list comprehension to build a list of
       log readings and process them::
       
           # print out the newest 10 stage readings in oldest to newest order
           from sl3 import *
           my_list = [r for r in Log(10, "stage")]
           my_list.reverse()
           for r in my_list:
               print(r)
               
    Search limit
        When searching for a matching label or time in the log, the Log class imposes a limit on
        the number if items that will be scanned called `limit`. This can be changed for all instances
        of the Log class or for just a specific instance. The default is just 1000 and that may not
        be sufficient if you want to search far back in the log. In this first example we will
        change that limit to one million for all future Log searches::
        
            >>> from sl3 import Log
            >>> Log.limit = 1000000
            >>> for reading in Log(5, "Reset Soft"):
            ...     print(reading)
            05/08/2017,22:21:16,Reset Soft,115,,G
            05/08/2017,22:19:58,Reset Soft,114,,G
            05/08/2017,22:11:54,Reset Soft,113,,G
            05/08/2017,17:59:44,Reset Soft,112,,G
            05/08/2017,16:12:37,Reset Soft,111,,G 
            
        Alternatively, the limit can be changed just on an instance of the Log class, leaving 
        the default limit of 1000 items in place::
        
            >>> from sl3 import Log
            >>> my_log = Log(5, "Reset Soft")
            >>> my_log.limit = 1000000
            >>> for reading in my_log:
            ...     print(reading)
            05/08/2017,22:21:16,Reset Soft,115,,G
            05/08/2017,22:19:58,Reset Soft,114,,G
            05/08/2017,22:11:54,Reset Soft,113,,G
            05/08/2017,17:59:44,Reset Soft,112,,G
            05/08/2017,16:12:37,Reset Soft,111,,G 
    """

    count = None
    """ number of Readings to iterate"""

    match = None
    """a label to match"""

    oldest = None
    """ a oldest time to match"""

    newest = None
    """a newest time to match"""

    limit = 1000
    """ a limit on the number entries to search when looking for a match"""

    def __init__(self, count=None, match=None, oldest=None, newest=None, pos=LOG_NEWEST):
        """
        Creates an instance of the log class.
        
        :param count: limit the number of log entries read
        :param match: label value to match
        :param oldest: match entries greater than or equal to this time
        :param newest: match entries less or equal to this time
        :param pos: specify the start position in the log (defaults to LOG_NEWEST)

                    ===========   ===================================================================
                    Option        Description
                    ===========   ===================================================================
                    LOG_CURRENT   Does not change the position. Whenever the script is loaded (or 
                                  reloaded), the position will pointed to the newest data in the log 
                                  and set to retrieve newer data as it's logged.
                    LOG_NEWEST    Log readings will be retrieved from the newest part of the log,
                                  moving towards older data.
                    LOG_OLDEST    Log readings will be retrieved from the oldest part of the log,
                                  moving towards the newer data.
                    ===========   ===================================================================
        """
        self.__set_match(count, match, oldest, newest, pos)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            if self.count is not None:
                if self.count > 0:
                    self.count -= 1
                    return self.next()
                else:
                    self.count = None
                    raise StopIteration
            else:
                return self.next()
        except (LogAccessError, AttributeError):
            raise StopIteration

    def __set_match(self, count=None, match=None, oldest=None, newest=None, pos=LOG_NEWEST):
        self.count = count
        self.match = match
        self.oldest = oldest
        self.newest = newest
        self.pos = pos
        return self

    def __is_match(self, time, label):
        if (self.match is not None) and (label != self.match):
            return False
        if (self.oldest is not None) and (time < self.oldest):
            return False
        if (self.newest is not None) and (time > self.newest):
            return False
        return True

    def get_newest(self):
        """
        Returns the newest entry in the log
       
        :rtype: Reading
        :raises: LogAccessError
        """
        entry = get_newest_entry()
        limit = self.limit
        self.pos = None
        while not self.__is_match(entry[0], entry[1]):
            limit -= 1
            if limit <= 0:
                raise LogAccessError("limit exceeded", self.limit)
            entry = get_older_entry()
        return Reading(entry)

    def get_oldest(self):
        """
        Returns the oldest entry in the log
               
        :rtype: Reading
        :raises: LogAccessError
        """
        entry = get_oldest_entry()
        limit = self.limit
        self.pos = None
        while not self.__is_match(entry[0], entry[1]):
            limit -= 1
            if limit <= 0:
                raise LogAccessError("limit exceeded", self.limit)
            entry = get_newer_entry()
        return Reading(entry)

    def get_newer(self):
        """
        Returns the next newer entry in the log
               
        :rtype: Reading
        :raises: LogAccessError
        """
        if self.pos:
            if self.pos == LOG_NEWEST:
                entry = get_newest_entry()
            else:
                entry = get_oldest_entry()
            self.pos = LOG_CURRENT
        else:
            entry = get_newer_entry()
        limit = self.limit
        while not self.__is_match(entry[0], entry[1]):
            limit -= 1
            if limit <= 0:
                raise LogAccessError("limit exceeded", self.limit)
            entry = get_newer_entry()
        return Reading(entry)

    def get_older(self):
        """
        Returns the previous older entry in the log
        
        :rtype: Reading
        :raises: LogAccessError
        """
        if self.pos:
            if self.pos == LOG_NEWEST:
                entry = get_newest_entry()
            else:
                entry = get_oldest_entry()
            self.pos = LOG_CURRENT
        else:
            entry = get_older_entry()
        limit = self.limit
        while not self.__is_match(entry[0], entry[1]):
            limit -= 1
            if limit <= 0:
                raise LogAccessError("limit exceeded", self.limit)
            entry = get_older_entry()
        return Reading(entry)

    def next(self):
        """
        Returns either the next newer or previous older entry depending on whichever direction was retrieved last.
        By default, the most recent entries that have been added to the log since the script started running is returned.

        :rtype: Reading
        :raises: LogAccessError
        """
        if self.pos:
            if self.pos == LOG_NEWEST:
                entry = get_newest_entry()
            else:
                entry = get_oldest_entry()
            self.pos = LOG_CURRENT
        else:
            entry = get_entry()
        limit = self.limit
        while not self.__is_match(entry[0], entry[1]):
            limit -= 1
            if limit <= 0:
                raise LogAccessError("limit exceeded", self.limit)
            entry = get_entry()
        return Reading(entry)


def wait_for(device, pattern):
    """
    Wait for a pattern of bytes to be received over a communications device

    :param Serial device: Any Serial, File, or Stream object with a read() method.
    :param str pattern: A string to look for in the input stream of the device.
    :return: True if a match was found or False if a timeout occured.
    :rtype: bool

    patterns::
        * a "?" in the pattern will match any single character
        * a "*" will match anything (ie "A*G" would match "ABCDEFG")
        * control characters may be embedded with "^" (ie "^C" would match a ctrl-c)
        * special characters may also be embedded with "\" (ie "\xff" would match a 255 ascii)
        * any of the special codes may be matched by escaping with a "\" (ex: "\\*")
          wait_for is written to accept either byte or string oriented devices and patterns

    """
    pos = 0
    pattern_len = len(pattern)
    if pattern_len == 0:
        return False
    QUESTION = ord('?')
    STAR = ord('*')
    CARET = ord('^')
    SLASH = ord('\\')
    p = pattern[0]
    while pos < pattern_len:
        ch = device.read(1)
        if not ch:
            return False
        ch = ord(ch)
        p = ord(pattern[pos])
        if p == QUESTION:
            pos += 1
        elif p == STAR:
            if (pos + 1) >= pattern_len:
                return True
            if ch == ord(pattern[pos + 1]):
                pos += 2
        elif p == CARET:
            if (pos + 1) >= pattern_len:
                return True
            if ch == ord(pattern[pos + 1]) - ord('@'):
                pos += 2
            else:
                pos = 0
        elif p == SLASH:
            if (pos + 1) >= pattern_len:
                return True
            if ch == ord(pattern[pos + 1]):
                pos += 2
            else:
                pos = 0
        else:
            if ch == p:
                pos += 1
            else:
                pos = 0
    return True


def bin_to_str(num, count):
    """
    Converts a number in to a (count) byte long binary string. For example, bin(65,1) would return b'A'. If the number is a
    floating point number, then count must be either 4 or 8 to have the number stored in IEEE 32 bit or 64 bit single or double
    precisions respectively. If the count is not 4 or 8 (or -4 or -8), then the number is treated as an integer.
    The sign of count determines the byte order. When count is positive, the most significant byte is stored first
    (Compatible with ARGOS 8-bit binary formats). When count is negative, the least significant byte is stored first.

    Example::

        >>> import sl3
        >>> sl3.bin_to_str(1094861636, 4)
        b'ABCD'

    :param int,float num: Integer or float number to be converted to byte string
    :param int count: Number of bytes to converted num to. Byte count must be large enough to hold the number passed in.
    :return: Returns binary string representation of the number passed in.
    :rtype: bytes
    """
    import struct
    if isinstance(num, int) or (isinstance(num, float) and (abs(count) != 4 and abs(count) != 8)):
        num = round(num)
        # if count is positive, use big endian (high bytes first), else use little endian when converting num to bytes.
        bin_str = (struct.pack('>i', num))[-count:] if (count > 0) else struct.pack('<i', num)[:abs(count)]

    elif count > 0:
        if count == 4:
            bin_str = struct.pack('>f', num)  # 32 bit floating point byte string, big endian
        else:
            bin_str = struct.pack('>d', num)  # 64 bit floating point byte string, big endian

    else:
        if abs(count) == 4:
            bin_str = struct.pack('<f', num)  # 32 bit floating point byte string, little endian
        else:
            bin_str = struct.pack('<d', num)  # 64 bit floating point byte string, little endian

    return bin_str


def bit_convert(string, type):
    """
    Converts a binary string of specific format tye into a number. This is the opposite of bin function. The following types
    are supported:
    
        =====   =========================================================
        Type    string contents
        =====   =========================================================
        1       4 byte integer, least significant byte (LSB) first
        2       4 byte integer, most significant byte (MSB) first
        3       IEEE 754 32 bit float, least significant byte (LSB) first
        4       IEEE 754 32 bit float, most significant byte (MSB) first
        5       IEEE 754 64 bit float, least significant byte (LSB) first
        6       IEEE 754 64 bit float, most significant byte (MSB) first
        =====   =========================================================

    Example::
    
        >>> import sl3
        >>> sl3.bit_convert(b'DCBA', 1)
        1094861636
        >>> sl3.bit_convert(b'@\\x9c\\xcc\\xcd', 4)
        4.9

    :param bytes string: A string of bytes to be converted to a number.
    :param int type: See above table for valid options.
    :return: Returns the integer or float value representing the byte string passed in.
    :rtype: int or float
    """

    import struct
    if type == 1:
        num = struct.unpack('<i', string)[0]  # 4 byte integer, least significant byte (LSB) first, little endian
    elif type == 2:
        num = struct.unpack('>i', string)[0]  # 4 byte integer, most significant byte (MSB) first, big endian
    elif type == 3:
        num = struct.unpack('<f', string)[0]
    elif type == 4:
        num = struct.unpack('>f', string)[0]
    elif type == 5:
        num = struct.unpack('<d', string)[0]  # IEEE 754 64 bit float, least significant byte (LSB) first, little endian
    elif type == 6:
        num = struct.unpack('>d', string)[0]  # IEEE 754 64 bit float, most significant byte (MSB) first, Big endian

    return num


def bin6(num, count=3, right_digits=0, is_signed=True):
    """
    Converts a number in to a ``count`` byte long 6-bit packed binary string (used for GOES formatting).
    The maximum number of bytes is 3, which allows a representation range of [-131072 .. 131071].
    The more ``right_digits`` you request, the smaller the range. For instance with 2 ``right_digits``, the
    the maximum range becomes limited to [-1310.72 .. 1310.71], and even less with fewer bytes.
    
    Examples::
    
        >>> import sl3
        >>> # Convert 12345 to 6-bit pseudo-binary:
        >>> sl3.bin6(12345)
        b'C@Y'
        >>> # Convert BV in to a 3-byte 18-bit value:
        >>> BV = 12.32
        >>> sl3.bin6(BV, 3, 2)
        b'@SP'
        
    :param float num: A number to convert to pseudo-binary format. 
    :param int count: The number of bytes to format (1 to 3).
    :param int right_digits: The number of decimal digits to retain via scaling.
    :param bool is_signed: True if negative values should be allowed.
    :return: A byte string containing 6-bit binary data.
    :rtype: bytes
    """

    # Make sure num bytes is within the allowed range.
    count = max(min(count, 3), 1)

    # Pre-allocate a byte array of the desired length.
    result = bytearray(count)

    max_val = [[63, 4095, 262143], [31, 2047, 131071]]
    min_val = [[0, 0, 0], [-32, -2048, -131072]]
    mask = [0x0000003F, 0x00000FFF, 0x0003FFFF]

    # Scale and round the value based on the allowed range and number of right digits desired.
    scaled = round(num * 10 ** right_digits)
    scaled = min(scaled, max_val[is_signed][count - 1])
    scaled = max(scaled, min_val[is_signed][count - 1])

    # Format the result.
    for i in range(count):
        cbyte = (scaled & mask[i]) >> (i * 6)
        result[count - i - 1] = 63 if cbyte == 63 else cbyte + 64

    return bytes(result)


def batt():
    """
    Measures Satlink's supply voltage
    :return: battery voltage
    :rtype: float
    """
    return internal_sensor(0)


def internal_temp():
    """
    Measures Satlink's internal temperature sensor
    :return: temperature in Celsius
    :rtype: float
    """
    return internal_sensor(1)


def command_line(command, buf_size=512):
    """
    Issue commands to Satlink's command line.

    :param str command: command line function to execute, e.g. "Hello"  "M1 LAST"
    :param int buf_size: size of buffer for reply
    :return: command line reply
    :rtype: str
    """
    return c_command_line(command, buf_size)


def tls():
    """
    The tls() function returns a structure that may be used to store thread-local storage variables 

    In Python, when you create a global variable, every task, every custom format routine, 
    and every measurement may access that variable.  That  can be useful when data must be shared,
    but sometimes separate storage is needed that is unique to the script task, formatter, or 
    measurement That is what the tls() function provides.
        
    Creating a value in thread local storage is done by assigning a name in tls a value:
        tls().daily_rain = 100.0
    
    Referencing a variable stored in thread local storage is just as simple:
        tls().daily_rain = tls().daily_rain + hourly_rain
    
    But how can we tell if a variable already exists so we can tell whether we need to initialize it?
    We can use hasattr().  The code below initializes daily rainfall::
    
        if not hasattr(tls(), "daily_rain"):
            tls().daily_rain = 0.0

    We can also use getattr() to retrieve a value regardless of whether one exists in tls().
    The code below will retrieve a value for slope if one has been stored in tls(), otherwise use 1.0:"::

        slope = getattr(tls(), "slope", 1.0)

    Finally, tls is not limited to simple values. Any data-type that can be assigned to a 
    variable may be stored including strings, lists, and other objects.
    """
    return c_tls()


def setup_read(parameter):
    """
    Read SL3 setup for specified parameter.
    Examples::

        >>> From sl3 import *
        >>> setup_read("station name")
        "Sutron Satlink 3"
        >>> setup_read("recording")
        "On"

    :param str parameter: SL3 setup value to read
    :return: parameter value in SL3
    :rtype: str
    """
    return command_line(parameter).strip()


def setup_write(parameter, value):
    """
    Change setup for specified parameter. Nothing is returned if write is successful. A SetupError will be raised if write failed.
    
    Examples::

        >>> From sl3 import *
        >>> setup_write("station name", "Little Creek")
        >>> setup_write("M1 slope", 1.5)

    :param str parameter: SL3 setup parameter to change.
    :param value: Value to change the setup to. Can be str, bytes, float, int.
    :return: Nothing is returned if successful. Raises ``SetupError`` if the write failed or 
             the setup did not take on the exact value. 
    """
    result = command_line(parameter + "=" + str(value)).strip()
    if result:
        raise SetupError(result)


def crc(data, polynomial, initial_value=0, reflect=False, invert=False, reverse=False):
    """
    Computes the CRC-16 over ``data``
    The following web site contains a lot of details on different CRC implementations,
    those details compromise the variables passed in to the crc function:
    
       http://protocoltool.sourceforge.net/CRC%20list.html
    
    Example::
    
      >>> from sl3 import *
      >>> hex(crc("123456789", 0x1021))
      '0x31c3'
    
    :param str data: A str or bytes to compute a CRC across.
    :param int polynomial: A 16-bit number that varies based on the type of CRC and determines how the CRC operates.
    :param int initial_value: The intial value for the generator, typically 0, or 0xffff.
    :param bool reflect: There are two common versions of the CRC-16 algorithm, one that works 
                         by shifting the polynomial value left on each operation (normal), and one
                         that works by shifting the reflected polynomial value right on each operation.
    :param bool invert: True to invert the result. Some variations require this.
    :param bool reverse: True to reverse the final byte order. Some variations require this.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, polynomial, initial_value, reflect, invert, reverse)


def crc_xmodem(data):
    """
    Computes the Xmodem CRC-CCITT over ``data``
    
    :param str data: A str or bytes to compute a CRC across.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, 0x1021, 0, False, False, False)


def crc_ssp(data):
    """
    Computes the SSP CRC-16 over ``data``
    
    :param str data: A str or bytes to compute a CRC across.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, 0x8005, 0, True, False, False)


def crc_modbus(data):
    """
    Computes the ModBus CRC-16 over ``data``
    
    :param str data: A str or bytes to compute a CRC across.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, 0x8005, 0xffff, True, False, False)


def crc_kermit(data):
    """
    Computes the Kermit CRC-CCITT over ``data``
    
    :param str data: A str or bytes to compute a CRC across.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, 0x1021, 0, True, False, True)


def crc_dnp(data):
    """
    Computes the DNP CRC over ``data``
    
    :param str data: A str or bytes to compute a CRC across.
    :return: The computed 16-bit CRC value
    :rtype: int
    """
    return c_crc(data, 0x3d65, 0, True, True, True)


power_ports = ['SW1', 'SW2', 'PROT12', 'RS232', 'VREF', 'PREF']


def _power_validate_port(port):
    """
    Tells whether the provided parameter is a valid power port

    :param port: string indicating port
    :return: Boolean indicating whether the port is valid
    """
    if port.upper() in power_ports:
        return True
    else:
        raise ValueError("Not a valid port: " + port)


def power_control(port, turn_on):
    """
    Controls the various power output lines.

    :param port: which port to drive, string: 'SW1', 'SW2', 'PROT12', 'RS232', 'VREF', 'PREF'
    :param turn_on: Boolean indicating whether to turn on (True) or turn off (False) the power output
    """

    if _power_validate_port(port):
        command = "POWER " + port.upper()
        if turn_on:
            command += " ON"
        else:
            command += " OFF"

        command_line(command)


def power_sample(port):
    """
    Samples one of the various power output lines.

    :param port: which port to sample, string: 'SW1', 'SW2', 'PROT12', 'RS232', 'VREF', 'PREF'
    :return: Boolean indicating whether the power output is on
    """

    if _power_validate_port(port):
        if "ON" in command_line("POWER " + port.upper()).upper():
            return True
        else:
            return False


def _power_test():
    """
    tests out the power functions
    please note that the PREF output requires the programmable voltage expansion card
    """
    for port in power_ports:
        power_control(port, True)
        if not power_sample(port):
            raise AssertionError("Failed to turn on power port ", port)
        power_control(port, False)
        if power_sample(port):
            raise AssertionError("Failed to turn off power port ", port)


output_ports = ['OUTPUT1', 'OUTPUT2']


def _output_validate_port(port):
    """
    Tells whether the provided parameter is a valid output port

    :param port: string indicating port
    :return: Boolean indicating whether the port is valid
    """
    if port.upper() in output_ports:
        return True
    else:
        raise ValueError("Not a valid port: " + port)


def output_control(port, turn_on):
    """
    Drives the digital output lines

    :param port: which output to drive, string.  options are 'OUTPUT1', 'OUTPUT2'
    :param turn_on: whether to turn on or off the output, Boolean
    """

    if _output_validate_port(port):
        command = port.upper()
        if turn_on:
            command += " ON"
        else:
            command += " OFF"

        command_line(command)


def output_sample(port):
    """
    Samples one of the output lines.

    :param port: which output to drive, string.  options are 'OUTPUT1', 'OUTPUT2'
    :return: Boolean indicating whether the output is on
    """

    if _output_validate_port(port):
        if "NOT ACTIVE" in command_line(port.upper()).upper():
            return False
        else:
            return True


def _output_test():
    """
    tests out the output functions
    """
    for port in output_ports:
        output_control(port, True)
        if not output_sample(port):
            raise AssertionError("Failed to turn on output ", port)
        output_control(port, False)
        if output_sample(port):
            raise AssertionError("Failed to turn off output ", port)


def sgn(number):
    """
    Returns an integer indicating the sign of provided number

    :param number: number whose sign we are interested in
    :type number: integer
    :return: the sign of the number: 1 when above 0, returns 0 when 0, and returns –1 when negative
    :rtype: integer
    """
    if number > 0:
        return 1
    elif number == 0:
        return 0
    elif number < 0:
        return -1


def _reset_count_parse(reply):
    """
    Prases the number of resets from the DIAG command

    :param reply: command line reply string
    :return: number of resets
    :rtype: integer
    """
    import re

    resets = 0
    lines = reply.strip().split("\r\n")
    for line in lines:
        resets += int(re.search(r' \d+', line).group(0))

    return resets


def reset_count():
    """
    Tells you how many times Satlink has reset

    :return: number of resets
    :rtype: integer
    """
    return _reset_count_parse(command_line("DIAG"))


def _ver_parse(reply):
    """
    parses the version from the command line reply for ver()

    :param reply: command line reply to VER
    :type reply: string
    :return: major, minor, and revision
    :rtype: tuple
    """
    major, minor, rev = 0, 0, 0

    # first line has the info
    first_line = reply.strip().split("\r\n")[0]

    # split it into words
    words = first_line.split()

    ver_next = False  # is the next word the version?
    rev_next = False  # is the next word the revision?

    # loop over all the words, looking for version and revision
    for word in words:
        # check for ver_next and rev_next BEFORE setting them
        if ver_next:
            # parse out the major and minor version from a string like "8.10"
            ver_next = False
            mm = word.strip().split('.')
            major = int(mm[0])
            minor = int(mm[1])

        if rev_next:
            # parse out the revision.  string is a number like 2345
            rev_next = False
            rev = int(word.strip())

        # set ver_next and rev_next AFTER checking for them
        if "VERSION" in word.upper():
            # next word has the major and minor
            ver_next = True

        if "REVISION" in word.upper():
            # next word has the revision
            rev_next = True

    return [major, minor, rev]


def ver():
    """
    Tells the Satlink software version::

        >>> ver()
        [8, 10, 2578]

    :return: major, minor, and revision
    :rtype: tuple
    """
    return _ver_parse(command_line("VER", 2048))


def ver_boot():
    """
    Tells the Satlink bootloader software version::

        >>> ver_boot()
        [8, 10, 0]

    :return: major, minor, and revision.  revision is always 0 for bootloader
    :rtype: tuple
    """
    return _ver_parse(command_line("VER", 2048))


def clear_stats():
    """Clears Satlink's counters, including transmission counts, reset counts, and more"""
    command_line("STATUS 0")


def trigger_meas(meas_index):
    """
    Initiates a live reading of said measurement.  Does not wait for measurement to complete.

    :param meas_index: measurement index int,  1 to 32.  Use 0 to trigger all measurement.
    :return: None
    """
    if meas_index == 0:
        command_line("MEAS TRIGGER")
    else:
        command_line("M{} MEAS TRIGGER".format(meas_index))


def trigger_script_task(task_index):
    """
    Initiates said script task.  Does not wait for completion.

    :param task_index: Script task index int, 1 to 8.  Use 0 to trigger all tasks.
    :return: None
    """
    if task_index == 0:
        command_line("SCRIPTRUN TRIGGER")
    else:
        command_line("S{} SCRIPTRUN TRIGGER".format(task_index))


def trigger_tx(tx_index):
    """
    Initiates a transmission.  Does not wait for transmission to complete.

    :param tx_index: Index of transmission.  You may not trigger all transmissions by passing in 0.
    :return: None
    """
    command_line("TX{} TXNOW".format(tx_index))


def meas_find_label(meas_index):
    """Returns the customer set Label of the measurement."""

    return setup_read("M{} Label".format(meas_index))


def meas_find_index(meas_label):
    """
    Tells you the index of the measurement

    :param meas_label: the customer set label for the measurement
    :type meas_label: string
    :return: measurement index if a match is found.  zero if no match is found
    :rtype: int
    """
    for index in range(1, 32 + 1):
        if meas_label.upper() == meas_find_label(index).upper():
            return index

    return 0  # no measurement with that label found
