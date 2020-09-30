from sl3 import *
from serial import Serial
from time import sleep, time, localtime
from os import ismount, exists, mkdir

# StarDot.py (C) 2020 Ott Hydromet, version 1.0
#
# Purpose:
#
# This script will capture still jpeg images from a StarDot camera using the RS232 port of the XL2 and the camera and
# archive them to an SDHC card and also store them for transmission. Power to the camera is automatically controlled
# by the XL2 using switched power. The images are stored in daily folders created under /sd/Sutron/StarDot and in
# the /sd/TX1 folder for transmission and automatic deletion. The way the images are named and stored can
# be modified by editing the imageFolder, txFolder, and imageFileName global variables. You may also select whether
# you want the power to the camera to always be on, whether to sync time to the camera, and whether to modify the
#
# The script will not try to capture an imagine if an SDHC card is not inserted. The SDHC card will also eventually
# fill up if not periodically replaced or the pictures on the card deleted.
#
# Using the script is very simple. Just schedule it to run as frequently as you wish to capture a picture.
# The fastest it can be scheduled is about once per minute in order to leave time to power on the camera,
# and transfer the image.
#
# You may also make changes to the camera settings directly via the camera's web pages, and they will stick
# (except for the overlay unless you disable that in the program). For instance, you may wish to reduce the
# image size and the FPS to reduce time to capture the image, storage, and power consumption. You may also
# wish to enable automatic day/night mode so the IR LEDs of the camera will turn on as needed.
#
#
# Tested with:
#
# StarDot NetCam CAM-SEC5IR
# - with the RS232 port of the XLink500 connected to the serial port of the StarDot
#   and Switched Power 1 of the XLink500 connected to the DC12V input of the camera.
# - a null modem cable is not required.
#

#
# The camera may occasionally fail a transfer due to a reboot or shutdown with messages like this:
#       "lsz: caught signal 15; exiting\r\n[~]#"
# Sometimes the camera will reset in the middle of an operation with the message:
#       "HARDWARE RESET"
# This is most likely to happen if power to the camera is left on all the time (leavePowerOn is set to True)
#

# the camera's command prompt:
cameraPrompt = "]# "

# command to copy the current image to a file we can transfer
copyCommand = "cp /dev/video/jpeg0 /var/tmp/image.jpg\r"

# command to initiate ymodem send of an snapshot
transferCommand = "lsz -b /var/tmp/image.jpg\r"

# where to store each snapshot
imageFolder = "/sd/Sutron/StarDot/{YYYY}{MM}{DD}"

# where to store each snapshot
imageFileName = "StarDot_{YY}{MM}{DD}{hh}{mm}{ss}.jpg"

# where to store images for transmission
txFolder = "/sd/TX1"

# setting to enable h/w handshaking on the serial port
hwHandshake = True

# have the SL3 update the time in the camera
timeSync = True

# option to leave the camera on (except in case of an error) to permit capturing pictures more often
leavePowerOn = False

# how the camera is powered: None, "SW1", "SW2", "PROT12", "SDI1" or "SDI2"
portPower = "SDI1"

# update the image overlay the first time the script runs
updateOverlay = True

totalPictures = 0
totalFails = 0
totalRetries = 0
totalNoSD = 0
lastLength = 0

SOH         = chr(0x01)  # CTRL-A
STX         = chr(0x02)  # CTRL-B
EOT         = chr(0x04)  # CTRL-D
ACK         = chr(0x06)  # CTRL-F
NAK         = chr(0x15)  # CTRL-U
CAN         = chr(0x18)  # CTRL-X
CRC         = chr(0x43)  # "C"

class YmodemError(Exception):
    pass

class SDCardNotMountedError(Exception):
    pass

def TurnCamera(state):
    """
    Turn the camera on/off

    :param state: True turns the camera on, False turns it off
    :return: True if the camera is on
    """
    if not portPower:
        return True
    s = "On" if state else "Off"
    if portPower == "SDI1":
        cmd = "SDI PORT1 POWER "
    elif portPower == "SDI2":
        cmd = "SDI PORT2 POWER "
    else:
        cmd = "POWER {} ".format(portPower)
    return s in command_line(cmd + s)

def IsCameraOn():
    """
    Returns the state of power to the camera
    :return: True if the camera is on
    """
    if not portPower:
        return True
    if portPower == "SDI1":
        cmd = "SDI PORT1 POWER "
    elif portPower == "SDI2":
        cmd = "SDI PORT2 POWER "
    else:
        cmd = "POWER " + portPower
    return "On" in command_line(cmd)

def FormattedTimeStamp(timeStamp, dateTimeString):
    """
    Add time and data information to a string

    :param timeStamp: a time to use to format the string s
    :param dateTimeString: a string with key fields like {YYYY}{YY}{MM}{DD}{hh}{mm}{ss}
    :return: dateTimeString with the key fields replaced with the actual date/time information from timeStamp
    """
    t = list(localtime(timeStamp))
    # build up a dictionary we can use to translate from time / date keys to actual formatted values
    d = {"YYYY": "{:04}".format(t[0]) }
    t[0] %= 100
    for i,j in zip(["YY","MM","DD","hh","mm","ss","dow","julian"], t):
        d[i] = "{:02}".format(j)
    # time stamp the string by converting text fields like {YY} in the string to the 2-digit year, etc
    # with the help of the dictionary we setup to help us
    return dateTimeString.format(**d)

def GetOverlayText():
    """
    Get the text to be showed on the camera overlay

    :return: The default overlay setting with the station's name at the beginning
    """
    # customize the overlay displayed on the camera
    return " {} $P %a %b %d %H:%M:%S.$[ %Y \r\n Exposure: $E ($e) Frame: $n ".format(command_line("station name").strip())

def YmodemCheck(s, expect):
    ok = False
    seq = -100
    data = ""
    crc = -100
    if len(s) in [133, 1029] and chr(s[0]) in [SOH, STX] and s[1] == expect and (0xff - s[2]) == expect:
        seq = s[1]
        data = s[3:-2]
        crc = s[-2]<<8 | s[-1]
        ok = True
    return ok, seq, data, crc

def PurgeInput(port):
    t = port.timeout
    port.timeout = 0.01
    while port.read(256):
        pass
    port.timeout = t

def YmodemRead(port, sendByte):
    PurgeInput(port)
    port.write(sendByte)
    s = port.read(1)
    if s:
        if s[0] == ord(SOH):
            s += port.read(132)
        elif s[0] == ord(STX):
            s += port.read(1028)
    return s

def YmodemRecv(port, outputFile):
    global totalPictures, totalFails, totalRetries, lastLength
    currentLen = 0
    port.timeout = 3.0
    byteCANCEL = str_to_bytes(CAN)
    byteEOT = str_to_bytes(EOT)
    # an additional sleep to help purge out the Zmodem announce string
    sleep(0.1)
    retries = 0
    n = 0
    ok = False
    ack = CRC
    while retries < 10:
        # start Ymodem by sending a "C" to request CRC checking, and waiting for the file header
        s = YmodemRead(port, ack)
        # we check the header but do not need anything from it
        if YmodemCheck(s, n):
            ok = True
            break
        retries += 1
        ack = NAK

    if not ok:
        raise YmodemError("Camera sent unexpected Ymodem header packet", s)

    ack = ACK+CRC
    n = 1
    retries = 0
    cancels = 0
    ok = False
    while retries < 10:
        # send an ACK or NAK and read the next Ymodem packet from the camera
        s = YmodemRead(port, ack)
        ack = ACK
        ok, seq, data, crc = YmodemCheck(s, n)
        # check and make sure the crc was correct
        if crc == crc_xmodem(data):
            if ok:
                # packet is good, write it to disk
                n += 1
                outputFile.write(data)
                currentLen += len(data)
                retries = 0
            elif n == (seq+1)%256:
                # just received a re-transmission of a packet we already had, so we can ACK it
                ack = ACK
                totalRetries += 1
                retries += 1
            else:
                # something is wrong, let's request a retry
                ack = NAK
                totalRetries += 1
                retries += 1
        elif s == byteEOT:
            # if we recieved an EOT byte it indicates the end of the transfer
            # we just need to wrap up the Ymodem batch transfer
            ok = True
            s = YmodemRead(port, ACK)
            s = YmodemRead(port, CRC)
            s = YmodemRead(port, ACK)
            break
        elif s == byteCANCEL:
            cancel += 1
            if cancel > 3:
                break
        else:
            # the crc didn't check (probably a log message interfered) so NAK and retry
            ack = NAK
            totalRetries += 1
            retries += 1
        n %= 256

    # all done ... track statistics so we can report
    if ok:
        totalPictures += 1
        lastLength = currentLen
    else:
        PurgeInput(port)
        totalFails += 1

    return ok

def WaitPrompt(port):
    global totalFails
    if not wait_for(port, cameraPrompt):
        raise YmodemError("Camera did not provide a prompt")

def SendCommand(port, cmd):
    port.write(cmd)
    WaitPrompt(port)

def SetCameraTime(port):
    t = localtime(time())
    SendCommand(port, "date +%x -s \"{:02d}/{:02d}/{:02d}\"\r".format(t[1], t[2], t[0] % 100) )
    SendCommand(port, "date +%X -s \"{:02d}:{:02d}:{:02d}\"\r".format(t[3], t[4], t[5]) )
    SendCommand(port, "hwclock -w\r")

def UpdateOverlay(port, s):
    """
    Update the overlay displayed over the camera image

    :param port:        serial port
    :param s:           StarDot formatted string
    :return:            True if the overlay was updated
    """
    try:
        # We are using the sed command to modify the overlay file, but there are some special characters we
        # need to "escape" with a back slash or else sed will misinterpret them:
        special = "\\$.*[^"
        for ch in special:
            s = s.replace(ch, "\\" + ch)
        s = s.replace("\r", "\\\\r")
        s = s.replace("\n", "\\\\n")
        # use the linux stream editor to modify just the "overlay_text" line in the file and output to a temp file
        SendCommand(port, "sed 's/overlay_text=.*/overlay_text=\"{}\"/' /etc/config/overlay0.conf >/var/tmp/overlay0.conf\r".format(s))
        # copy the temp file back over the original
        SendCommand(port, "cp /var/tmp/overlay0.conf /etc/config/overlay0.conf\r")
        # make the changes made to overlay.conf permanent
        SendCommand(port, "config save\r")
    except YmodemError:
        return False
    return True

@TASK
def TakePicture():
    global totalPictures, totalFails, totalRetries, totalNoSD, lastLength, updateOverlay

    if not ismount("/sd"):
        totalNoSD += 1
        raise SDCardNotMountedError("SD card must be inserted to take pictures")

    if is_being_tested():
        print("This can take too long to run well as a test, so aborting...")
        return

    # capture the start time so we can provide some performance information
    t1 = time()
    t2 = t1
    ok = False
    try:
        t = time()
        folder = FormattedTimeStamp(t, imageFolder)
        fileName = FormattedTimeStamp(t, imageFileName)
        imagePath = folder + "/" + fileName

        if not exists(folder):
            command_line('FILE MKDIR "{}"'.format(folder))

        with open(imagePath, "wb") as outputFile:

            # the camera starts off at 38.4K baud on boot, but once we're logging in, we can increase it
            with Serial("RS232", 38400) as port:
                port.rtscts = hwHandshake
                if not hwHandshake:
                    port.dtr = True
                    port.rts = True
                # was the camera left powered up?
                if IsCameraOn():
                    # encourage the camera to re-issue the login prompt by sending a <CR>
                    port.write("\r")
                    port.timeout = 3.0
                else:
                    TurnCamera(True)
                    port.timeout = 45.0
                if not wait_for(port, " login: "):
                    raise YmodemError("Camera did not boot up and prompt for login")
                port.timeout = 3.0
                port.write("admin\r")
                if not wait_for(port, "Password: "):
                    raise YmodemError("Camera did not prompt for password")
                port.write("admin\r")
                WaitPrompt(port)
                # increase the baud rate to 115.2K kbaud
                port.write("stty 115200\r")
                sleep(0.25)

            # now communicate with the camera at 115.2K baud
            with Serial("RS232", 115200) as port:
                port.timeout = 3.0
                port.rtscts = hwHandshake
                if not hwHandshake:
                    port.dtr = True
                    port.rts = True
                PurgeInput(port)
                if timeSync:
                    # set the camera's time so hopefully it will stamp the picture with the actual time
                    SetCameraTime(port)
                # try to eliminate console messages (still seeing "init: /bin/mdnsd respawning too fast" messages)
                SendCommand(port, "dmesg -n 1\r")
                # copy the JPG image to a temporary file so it can't change on us while we1're sending it
                SendCommand(port, copyCommand)
                if updateOverlay:
                    if UpdateOverlay(port, GetOverlayText()):
                        print("Updated the camera's overlay")
                        # allow some time for a new picture to be taken with the updated overlay
                        sleep(0.5)
                        # the changes to the overlay should persist, so need need to continue updating it:
                        updateOverlay = False
                    else:
                        print("Failed to update the camera's overlay")
                t2 = time()
                # request the camera to send the image file using Ymodem
                port.write(transferCommand)
                # receive the file
                if YmodemRecv(port, outputFile):
                    print("Camera imaged stored to ", imagePath, lastLength, "bytes")
                    if leavePowerOn:
                        # abort anything in process
                        port.write(chr(3))
                        sleep(0.25)
                        # logout
                        port.write("exit\r")
                        sleep(0.25)
                    ok = True
                else:
                    raise YmodemError("Failed to capture picture")
        if ok and txFolder:
            if not exists(txFolder):
                command_line('FILE MKDIR "{}"'.format(txFolder))
            command_line('FILE COPY "{}" "{}"'.format(imagePath, txFolder + "/" + fileName))

    except Exception as e:
        totalFails += 1
        raise e
    finally:
        if not leavePowerOn or not ok:
            TurnCamera(False)
        t3 = time()
        print("Total Pictures", totalPictures, "Failures", totalFails, "Retries", totalRetries, "No SD Card", totalNoSD)
        print("Startup Time (secs)", int(t2-t1))
        print("Transfer Time (secs)", int(t3-t2))
        print("Throughput", int(lastLength/(t3-t2)), "bytes per sec")
