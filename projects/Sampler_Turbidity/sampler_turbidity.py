""" Triggers ISCO sampler via SDI-12 command, based on a turbidity measurement, and the time of the last sample

    To use script:
        1) Setup a turbidity measurement and connect it to the sampler_turbidity function
        2) Setup General Purpose Variables:
            GP1 is the Threshold (if turbidity exceeds threshold, sampler may be triggered)
            GP2 is the Sampling Interval Minimum (how much time must pass between sample triggers)
        3) Setup Script Task S1 with function trigger_sampler to be initiated on button press (also trigger by issuing !S1 SCRIPTRUN)
        4) Configure the details of the SDI-12 module that triggers the sampler below
        5) Check Script Status to see how the script is doing (or issue !STATUS SCRIPT command)

"""

""" SDI-12 module that triggers the sampler"""
# what address the sampler is on
sdi_addy = 0

# what command to issue to trigger sampler
sdi_cmd = 'M'

# what bus is the sampler on
sdi_bus = "PORT1"



""" Variables used by program, reset at boot """
# We count how many samples were triggered
samples_triggered = 0

# Time sampler was triggered last.  0 means never
time_last_sample = 0.0

# Turbidity that triggered last sample
turbidity_last = 0.0

# the sampler will tell us which slot was triggered
last_sample_slot = -1


import utime
from sl3 import *


class Sdi12Error(Exception):
    pass


def sdi_bus_valid(sdi_bus):
    """
    Routine checks whether the provided parameter is a SDI-12 bus

    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: True if provided parameter is a valid bus
    :rtype: Boolean
    """
    bus_upper = sdi_bus.upper()
    if ("PORT1" in bus_upper) or ("PORT2" in bus_upper) or ("RS485" in bus_upper):
        return True
    else:
        return False


def sdi_send_command_get_reply(cmd_to_send, sdi_bus="Port1"):
    """
    Sends provided command out on the specified SDI-12 bus, gets reply from the sensor.

    :param cmd_to_send: the command to send on the SDI-12 bus, e.g. "0M!"
    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: sensor reply, or "No reply"
    :rtype: str
    """

    if sdi_bus_valid(sdi_bus):
        reply = command_line('!SDI {} {}'.format(sdi_bus, cmd_to_send), 128)
        if "Got reply: " in reply:
            reply = reply.replace("Got reply:", "")
    else:
        raise Sdi12Error("No such bus", sdi_bus)

    reply = reply.strip()
    return reply


def sdi_collect(address, command="M", sdi_bus="Port1"):
    """
    Collects data from an SDI-12 sensor using the provided cmd_to_sensor
     It is expected that the sensor will use the same reply format as to aM! cmd_to_sensor

    :param address: int address of SDI-12 sensor to collect data from
    :param command: command to issue to sensor, e.g. "M"
    :param sdi_bus: string indicating bus: "Port1", "Port2", or "RS485"
    :return: a list of floats containing all the returned parameters
    """

    # create the SDI-12 cmd_to_sensor using the provided address
    cmd_to_sensor = '{0}{1}!'.format(address, command)

    # issue the cmd_to_sensor and get the reply
    sensor_reply = sdi_send_command_get_reply(cmd_to_sensor, sdi_bus)

    # parse out the returned values
    parsed = re.match('(\d)(\d\d\d)(\d)', sensor_reply)
    if parsed is None or int(parsed.group(1)) != address:
        raise Sdi12Error('No reply or bad reply', sensor_reply)

    # figure out how long and then wait for sensor to be ready
    time_till_reply = int(parsed.group(2))
    utime.sleep(time_till_reply)

    # how many parameters did the sensor return?
    values_returned = int(parsed.group(3))

    # all the parameters returned by the sensor end up here
    result = []

    # we will use this expression to parse the values form the sensor reply
    float_match = re.compile('([-+][0-9]*\.?[0-9]+[eE][-+]?[0-9]+)|([-+][0-9]*\.?[0-9]*)')

    # we need to issue one or more send data commands to the sensor
    data_index = 0
    while len(result) < values_returned and data_index <= 9:
        # create and issue the get data cmd_to_sensor
        cmd_to_sensor = '{0}D{1}!'.format(address, data_index)
        sensor_reply = sdi_send_command_get_reply(cmd_to_sensor, sdi_bus)

        if (sensor_reply is None) or (sensor_reply == "No reply"):
            raise Sdi12Error('Missing data at pos', len(parsed) + 1)

        # parse out all the values returned by the sensor
        while len(result) < values_returned:
            parsed = float_match.search(sensor_reply)
            if parsed is None:
                break
            result.append(float(parsed.group(0)))
            sensor_reply = sensor_reply.replace(parsed.group(0), '', 1)

        data_index += 1
    return result


def activate_sampler():
    """
    Issues an SDI-12 command to trigger the sampler
    Sampler replies with the sample slot

    :return: sample slot number (-1 means error)
    :rtype: int
    """
    try:
        sdi_reply = sdi_collect(sdi_addy, sdi_cmd, sdi_bus)
        sample_slot = int(sdi_reply[0])

    except (Sdi12Error, ValueError):
        sample_slot = -1

    return sample_slot


def trigger_sampler_low():
    """Triggers the sampler immediately and logs it."""

    global samples_triggered
    global time_last_sample
    global last_sample_slot

    # increment the number of samples
    samples_triggered += 1

    # update the time of the last sample
    time_last_sample = utime.time()

    # trigger the sampler
    last_sample_slot = activate_sampler()

    # quality - if the sample failed, last_sample_slot is -1
    if last_sample_slot == -1:
        valid = 'B'
    else:
        valid = 'G'

    # write a log entry
    reading = Reading(label="Triggered", time=time_last_sample,
                      etype='E', value=last_sample_slot,
                      right_digits=0, quality=valid)
    reading.write_log()


def status_update(measurement=True, value=0.0):
    """
    Add diagnostic info to the script status

    :param measurement: is the update done by a manual trigger or a measurement
    :type measurement: Bool
    :param value: if measurement, what the Turbidity reading was
    :type value: float
    :return: None
    """
    global samples_triggered
    global time_last_sample
    global last_sample_slot

    print("Total samples triggered since boot: {}".format(samples_triggered))
    if time_last_sample:
        print("Last trigger: {}".format(ascii_time(time_last_sample)))

        if last_sample_slot >= 0:
            print("Last sample slot: {}".format(last_sample_slot))
        else:
            print("Last trigger FAILED SDI-12 error: {}".format(last_sample_slot))

        if measurement:
            print("Trigger turbidity: {}".format(value))
        else:
            print("Last trigger was done manually")

    else:
        print("Not triggered since bootup")


@TASK
def trigger_sampler():
    """ Setup a task to trigger the sampler unconditionally"""
    trigger_sampler_low()
    status_update(measurement=False)  # not a measurement, but a manual trigger


@MEASUREMENT
def sampler_turbidity(turbidity):
    """ Connect a measurement to this function to trigger
    the sampler based on turbidity"""
    sample_now = False

    threshold = float(setup_read("GP1 Value"))
    if threshold <= 0:
        # otherwise it is a bad setup
        print("Bad setup: Threshold is ", threshold)
    else:
        if turbidity > threshold:  # threshold is exceeded
            if time_last_sample == 0:
                # first sample since bootup
                sample_now = True
            else:
                # how often can we sample?
                min_time_interval = float(setup_read("GP2 Value"))

                if min_time_interval < 0:
                    print("Bad setup: Minimum Sampling Interval is ", min_time_interval)

                elif (time_scheduled() - time_last_sample) >= (min_time_interval * 60):
                    # it has been long enough since last sample
                    sample_now = True
                    turbidity_last = turbidity

    if sample_now:
        trigger_sampler_low()

    status_update(True, turbidity)
    print("Last turbidity: {}, {}".format(turbidity, ascii_time(time_scheduled())))

    return turbidity
