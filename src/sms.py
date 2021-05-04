# Example:  send an SMS (text) message to a phone number

from sl3 import *
import utime
    

def send_sms(phone_number, message):
    """
    Sends an SMS message.
    Only one message may be sent at a time.  System does not que messages!

    :param phone_number: the phone number to send message to, e.g. "+17034062800"
    :type phone_number: str
    :param message: the message to send, e.g. "Hello"
    :type message: str
    :return: None
    """
    command = ("SMS SEND {} more\n{}".format(phone_number, message))
    command_line(command)

    print("last message:")
    print(command)
    print("sent at " + ascii_time(utime.time()))


@TASK
def test_sms():
    """ tests the send_sms routine"""
    send_sms("+17034062800", "Hello from XLink.")

