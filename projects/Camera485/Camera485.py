from sl3 import *
from serial import Serial
from time import sleep, time, localtime
from os import ismount, exists, mkdir, rename, statvfs
from binascii import crc32

# Camera485.py (C) 2021 Ott Hydromet, version 2.0 (modified for lower compression, and added maxPictureSize setting)
#
# Purpose:
#
# This script will capture still jpeg images from a Camera485 camera using the RS485 port of the XL2 and the camera and
# archive them to an SDHC card and also store them for transmission. Power to the camera is automatically controlled
# by the XL2 using switched power. The images are stored in daily folders created under /sd/Sutron/Camera485 and in
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
# Tested with:
#
# Camera485
#   with the RS485 port of the XLink500 connected to the RS485 port of the Camera485
#   and Switched Power 1 of the XLink500 connected to the DC12V input of the camera.
#
#   XLink           Camera485
#   =========       ============
#   SW'D +12V  ...  Red Wire
#   GND        ...  Black Wire
#   RS485-A    ...  Yellow Wire
#   RS485-B    ...  White Wire
#
#

# where to store each snapshot
imageFolder = "/sd/Sutron/Camera485/{YYYY}{MM}{DD}"

# what to name each snapshot
imageFileName = "Camera485_{YY}{MM}{DD}{hh}{mm}{ss}.jpg"

# where to store images for transmission (None means do to store for tx)
txFolder = "/sd/TX1"

# option to leave the camera on (except in case of an error) to permit capturing pictures more often
leavePowerOn = False

# how the camera is powered: None, "SW1", "SW2", "PROT12", "SDI1" or "SDI2"
portPower = "SW1"

# how to use the IR LED's of the camera: "ON" for on all the time, None for auto switching
ledMode = None

# provide a text overlay to the camera to add to each image to display station name and a time stamp
useTextOverlay = True

# text overlay settings (when useTextOverlay is True)
overlayX = 10          # horizontal pixel position of overlay text
overlayY = 10          # vertical pixel position of overlay text
overlayFontSize = 16   # font height for overlay text

# address of camera on the RS-485 bus
defaultAddress = 1

# resolution to take pictures (see resolutionOptions below)
# - higher resolutions may fail to snap if the resulting image is bigger than the camera's buffer
#   and you will need to apply compression
defaultResolution = "1280x720"

# compression ratio(0 - 5) larger value is more compressed, 0 is the highest quality
defaultCompression = 3

# resolutions and compression levels to attempt in case the `defaultResolution` creates too large of an image for the camera
# ex: [("1920x1080", 3), ("1280x720", 1)]
retrySettings = []

# how many times to try an operation before failing
# (if one retry doesn't work, the camera probably needs to be power cycled)
defaultTries = 2

# how many times to cycle power before failing
defaultPowerCycles = 3

# how much data to request from the camera at a time
defaultPacketSize = 8192

# how long to wait for a reply to a command
defaultTimeout = 8.0

# number of seconds to wait after power on before trying to communicate with the camera
cameraWarmup = 3.5

# do not take a picture unless there are 64MB or more bytes free on the SDHC card
free_space_limit_take = 64

# do not archive a picture unless there are 256MB or more bytes free on the SDHC card
free_space_limit_archive = 256

# when using an auto setting, the s/w will repeat snapshots until it 
# finds the highest quality picture of less than this size
maxPictureSize = 450000

totalPictures = 0
totalFails = 0
totalRetries = 0
totalRepower = 0
totalNoSD = 0

resolutionOptions = {
    "640x480":5,"1280x960":6,"800x600":7,"1024x768":8,"1600x1024":10,"1600x1200":11,"1280x720":15,
    "1920x1080":16,"1280x1024":17,"480x270":30,"640x360":31,"800x450":32,"960x540":33,"1024x576":34,
    "1280x720_NEW":35,"1366x768":36,"1440x810":37,"1600x900":38 }

# what the camera sends when a snapshot is taken and the camera cannot hold it
out_of_memory = b"Len>JpegBufMaxLen\r\n"

class SDCardNotMountedError(Exception):
    pass

class SDCardLowOnSpace(Exception):
    pass

class CameraError(Exception):
    pass

class CameraMemoryError(CameraError):
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

def GetOverlayText(timeStamp):
    """
    Get the text to be showed on the camera overlay

    :return: The default overlay setting with the station's name at the beginning
    """
    # customize the overlay displayed on the camera
    return " {} {} ".format(
                        command_line("station name").strip(),                               # station name
                        FormattedTimeStamp(timeStamp, "{MM}/{DD}/{YYYY} {hh}:{mm}:{ss}")    # mm/dd/yyyy hh:mm:ss
                    )

def PurgeInput(port, timeout=0.01):
    try:
        t = port.timeout
        port.timeout = timeout
        while port.read(256):
            pass
    finally:
        port.timeout = t

def FormatCommand(addr, cmd, data):
    """
    Formats a command to the camera

    :param addr: address of camera (default is 1, 0 and 255 are the broadcast address)
    :param cmd: a camera protocol command byte
    :param data: data to be sent with the command (bytes)
    :return:
    """
    l = len(data)
    msg = bytes((addr, cmd)) + int.to_bytes(l, 2) + data
    crc = crc_xmodem(msg)
    return b"\x90\xeb" + msg + int.to_bytes(crc, 2)
    
def FormatSnapshot(addr=1, resolution="1920x1080", compression=1):
    """
    Creates a snapshot packet given the resolution and compression level

    :param addr:        camera address (default 1)
    :param resolution:  a valid resolution for the camera (ex: "1920x1080") see resolutionOptions
    :param compression: compression ratio (1-5) larger value is more compressed
    :return:            True if the overlay was updated
    """
    return FormatCommand(addr, 0x40, int.to_bytes(defaultPacketSize, 2) + bytes((resolutionOptions[resolution], compression)))

def CheckCrc(pkt):
    """
    Checks the CRC of a packet

    :param pkt: bytes of data
    :returns: True if the CRC was correct
    """
    return len(pkt) > 4 and crc_xmodem(pkt[2:-2]) == int.from_bytes(pkt[-2:])

def SendCommand(port, pkt, expectedLen=0, tries=3, is_snapshot=False):
    """
    Send a command to the camera and get the reply

    :param port: serial port with pre-configured timeout
    :param pkt: message to send
    :param expectedLen: the number of bytes in the message if known
    :param tries: how many attempts to make
    :return: the reply from the camera or None if a timeout or bad message
    """
    global totalRetries
    for _ in range(tries):
        port.reset_input_buffer()
        port.write(pkt)
        if expectedLen:
            msg = port.read(expectedLen)
        else:
            msg = port.read(6)
            if msg and msg[:2] == b"\x90\xeb" and msg[3] == pkt[3]:
                len = min(defaultPacketSize, int.from_bytes(msg[4:6]))
                msg += port.read(len+2)
        if msg and CheckCrc(msg):
            return msg
        elif is_snapshot and msg == out_of_memory:
            return msg
        elif tries > 1: # do not count tries when waiting for power up
            totalRetries += 1
    return None

def IsCameraReady(port, addr=1, timeout=10):
    """
    Check to see if the camera is powered up and ready to communicate

    :param port: serial port
    :param addr: address of camera (default is 1, 0 and 255 are the broadcast address)
    :param timeout: maximum time to wait
    :return: True if the camera is ready for communications
    """
    test_command = FormatCommand(addr, 0x01, b"\x55\xaa")
    old = port.timeout
    try:
        port.timeout = 0.25
        t = time()
        result = False
        while True:
            PurgeInput(port, 0.25)
            if SendCommand(port, test_command, 11, 1):
                result = True
                break
            if (time()-t) >= timeout:
                break
    finally:
        port.timeout = old
    return result

def SendSnapshot(port, snapshot, tries=3):
    """
    Sends a command to take a picture and returns the expected total length of the image

    :param port: serial port with pre-configured timeout
    :param snapshot: message to send
    :param tries: how many attempts to make
    :return: the number of bytes in the image or else None
    """
    pkt = SendCommand(port, snapshot, 19, tries, True)
    if pkt == out_of_memory:
        return pkt
    return int.from_bytes(pkt[7:11]) if pkt else None

def GetPartOfImage(port, addr, pos, numBytes, tries=3):
    """
    Retrieves part of an image that was snapped.

    :param port: serial port with pre-configured timeout
    :param addr: address of camera (default is 1, 0 and 255 are the broadcast address)
    :param pos: index in to the image to retrieve (32-bits)
    :param numBytes: number of bytes to retrieve
    :param tries: how many attempts to make
    :return: the piece of the image or None
    """
    pkt = SendCommand(port, FormatCommand(addr, 0x48, int.to_bytes(pos, 4) + int.to_bytes(numBytes, 2)),
                     8+numBytes, tries)
    return pkt[6:-2] if pkt else None

def UpdateOverlay(port, addr, x, y, font_size, text, tries=3):
    """
    Update the overlay displayed over the camera image

    :param port:        serial port
    :param addr:        address of camera (default is 1, 0 and 255 are the broadcast address)
    :param x:           horizontal pixel position of text overlay (0 is left)
    :param y:           vertical pixel position of the test overlay (0 is right)
    :param font_size:   pixel height of text font
    :param text:        string to be displayed (not bytes)
    :param tries: how many attempts to make
    :return:            True if the overlay was updated
    """
    cmd = FormatCommand(addr, 0x52, int.to_bytes(x, 2) + int.to_bytes(y, 2) + int.to_bytes(font_size, 1) + str_to_bytes(text))
    pkt = SendCommand(port, cmd, 8, tries)
    return True if pkt else False

def TurnLED(port, addr, state, tries=3):
    """
    Control's the LED of the camera

    :param port:        serial port
    :param state:       "ON", "OFF", or "AUTO" (is the default, and does not have a reply).
                        Unfortunately "OFF" only deactives an "ON", the LED will still turn
                        on automatically if there isn't enough light.
    :param tries:       how many attempts to make
    :return:            True if the overlay was updated
    """
    if state == "ON":
        data = b"\x33\x00"
    elif state == "OFF":
        data = b"\xcc\x00"
    elif state == "AUTO":
        data = b"\x33\x01"
    else:
        return False
    cmd = FormatCommand(addr, 0x07, data)
    pkt = SendCommand(port, cmd, 8, tries)
    return True if pkt or (state == "AUTO") else False

def AdjustDelay(port, addr, tries=3):
    """
    Adjust's the LED timing for the new camera model

    :param port:      serial port
    :param tries:     how many attempts to make
    :return:          True if the command was accepted
    """
    cmd = FormatCommand(addr, 0x78, b"\x78\x78\x1a\x1a")
    pkt = SendCommand(port, cmd, 10, tries)
    return True if pkt or (state == "AUTO") else False

def GetPicture(port, t, outputFile):
    if not IsCameraReady(port):
        raise CameraError("Camera is not communicating, is it connected?")
    if ledMode:
        if TurnLED(port, defaultAddress, ledMode, defaultTries):
            print("Turned LED", ledMode)
        else:
            print("Unable to turn LED", ledMode)
    if useTextOverlay:
        if UpdateOverlay(port, defaultAddress, overlayX, overlayY, overlayFontSize, GetOverlayText(t), defaultTries):
            print("Updated the camera's overlay")
        else:
            print("Failed to set the camera's text overlay")
    if AdjustDelay(port, defaultAddress, defaultTries):
        print("LED delay adjusted")
    else:
        print("Failed to adjust LED delay")

    # request the camera to take a snapshot
    imageLength = 0
    totalLength = SendSnapshot(port, FormatSnapshot(defaultAddress, defaultResolution, defaultCompression),
                               defaultTries)

    # if the snapshot was too big for the camera's RAM or just too big in general,
    # try backup resolution and compression levels
    if retrySettings:
        if totalLength == out_of_memory:
            ran_out = True
        else:
            ran_out = False
        if totalLength == out_of_memory or totalLength > maxPictureSize:
            for resolution, compression in retrySettings:
                totalLength = SendSnapshot(port, FormatSnapshot(defaultAddress, resolution, compression),
                                           defaultTries)
                if totalLength != out_of_memory and totalLength <= maxPictureSize:
                    if ran_out:
                        print("Using {} with compression {} due to lack of memory in camera to capture image".format(
                              resolution, compression))
                    else:
                        print("Using {} with compression {} to reduce the size of the image".format(
                              resolution, compression))
                    break

    if totalLength == out_of_memory:
        raise CameraMemoryError("Camera lacks memory to take snapshot, decrease resolution or increase compression")
    elif not totalLength:
        raise CameraError("Unable to snap image from camera")

    # receive the file in 8KB chunks
    while imageLength < totalLength:
        data = GetPartOfImage(port, defaultAddress, imageLength, min(totalLength - imageLength, defaultPacketSize),
                              defaultTries)
        if data:
            outputFile.write(data)
            imageLength += len(data)
        else:
            raise CameraError("Failed to retrieve camera image, received: " + str(imageLength))
    return imageLength

def CrcFile(name):
    """"
    Compute the CRC32 for a file

    :param name: the name of the file
    """
    result = 0
    with open(name, "rb") as f:
        while True:
            block = f.read(4096)
            if not block:
                break
            result = crc32(block, result)
    return result

def TakePicture(resolution, compression, retry_settings):
    global totalPictures, totalFails, totalRepower, totalRetries, totalNoSD
    global defaultResolution, defaultCompression, retrySettings

    if not ismount("/sd"):
        totalNoSD += 1
        raise SDCardNotMountedError("SD card must be inserted to take pictures")

    vfs = statvfs("/sd")
    free_space_mb = vfs[3] * vfs[0] / 1024 / 1024

    if free_space_mb < free_space_limit_take:
        raise SDCardLowOnSpace("SD card is too low on space to take a picture, {}MB free".format(free_space_mb))

    if not txFolder and (free_space_mb < free_space_limit_archive):
        raise SDCardLowOnSpace("SD card is too low on space to archive a picture, {}MB free".format(free_space_mb))

    defaultResolution = resolution
    defaultCompression = compression
    retrySettings = retry_settings

    # capture the start time so we can provide some performance information
    t1 = time()
    t2 = t1
    t3 = None
    ok = False
    imageLength = 0
    try:
        t = time()
        folder = FormattedTimeStamp(t, imageFolder)
        # the {CRC} field has to be post-processed, so, we need to rename it temporarily so as not to confuse FormattedTimeStamp
        fileName = FormattedTimeStamp(t, imageFileName.replace("{CRC}","\x01CRC\x01")).replace("\x01CRC\x01","{CRC}")
        imagePath = folder + "/" + fileName

        if not exists(folder):
            command_line('FILE MKDIR "{}"'.format(folder))

        with Serial("RS485", 115200) as port:
            port.rs485 = True
            port.timeout = defaultTimeout
            # size the input buffer a bit bigger than we need to reserve space for DMA buffers and other bytes
            port.set_buffer_size(defaultPacketSize * 11 // 8, None)

            exc = None
            for _ in range(defaultPowerCycles):
                with open(imagePath, "wb") as outputFile:
                    try:
                        t1 = time()
                        exc = None
                        # was the camera left powered up?
                        if not IsCameraOn():
                            TurnCamera(True)
                            sleep(cameraWarmup)
                        t2 = time()
                        imageLength = GetPicture(port, t, outputFile)
                        if imageLength:
                            ok = True
                            break
                    except CameraError as e:
                        exc = e
                    except CameraMemoryError as e:
                        # no reason to keep trying if the camera doesn't have enough RAM for the image
                        exc = e
                        break
                    finally:
                        if not leavePowerOn or not ok:
                            TurnCamera(False)
                    totalRepower += 1

        t3 = time()

        # we've exhausted all the power cycles and couldn't get a picture through, so re-raise the
        # exception related to the problem
        if exc:
            raise exc

        if ok:

            # replace "{CRC}" in the image path with the actual CRC32 of the image file
            if "{CRC}" in imagePath:
                crc = CrcFile(imagePath)
                newPath = imagePath.replace("{CRC}", hex(crc)[2:])
                rename(imagePath, newPath)
                imagePath = newPath
                fileName = fileName.replace("{CRC}", hex(crc)[2:])

            totalPictures += 1
            print("Camera imaged stored to ", imagePath, imageLength, "bytes")

            # copy the image to the transmission folder
            if txFolder:
                if not exists(txFolder):
                    command_line('FILE MKDIR "{}"'.format(txFolder))
                command_line('FILE COPY "{}" "{}"'.format(imagePath, txFolder + "/" + fileName))
                if free_space_mb < free_space_limit_archive:
                    command_line('FILE DEL "{}"'.format(imagePath))
                    raise SDCardLowOnSpace("SD card is too low on space to archive a picture, {}MB free".format(free_space_mb))

    except Exception as e:
        totalFails += 1
        raise e

    finally:
        if not t3:
            t3 = time()
        t4 = time()
        print("Total Pictures", totalPictures, "Failures", totalFails, "Repower", totalRepower, "Retries", totalRetries, "No SD Card", totalNoSD)
        print("Startup Time {:1.1f} secs".format(t2-t1))
        print("Transfer Time {:1.1f} secs".format(t3-t2))
        print("Total Time {:1.1f} secs".format(t4-t1))
        if t2 != t3:
            print("Throughput {:1.1f} bytes per sec".format(imageLength/(t3-t2)))

@TASK
def Take_1920x1080_Auto():
    if is_being_tested():
        return
    # try 1920x1080 with compression 3 first, but if that fails due to not enough RAM in the camera
    # retry at 1920x1080 with compression level 0 to 5; 1600x900 with 0 to 5, and 1280x720 with 0 to 3:
    retry_settings = [("1920x1080", _) for _ in range(0, 6)] + \
                     [("1600x900",  _) for _ in range(0, 6)] + \
                     [("1280x720",  _) for _ in range(0, 6)]
    TakePicture("1920x1080", 3, retry_settings)

@TASK
def Take_1280x720_MostDetail():
    if is_being_tested():
        return
    TakePicture("1280x720", 0, [])

@TASK
def Take_1280x720_MediumDetail():
    if is_being_tested():
        return
    TakePicture("1280x720", 2, [])

@TASK
def Take_1280x720_LeastDetail():
    if is_being_tested():
        return
    TakePicture("1280x720", 5, [])

@TASK
def Take_480x270():
    if is_being_tested():
        return
    TakePicture("480x270", 3, [])

@MEASUREMENT
def Free_Space_MB(data):
    # allows the user to measure/log the free space on the SDHC card in megabytes
    if not ismount("/sd"):
        raise SDCardNotMountedError("SD card must be inserted to take pictures")
    vfs = statvfs("/sd")
    if not ismount("/sd"):
        raise SDCardNotMountedError("SD card must be inserted to take pictures")
    free_space_mb = vfs[3] * vfs[0] / 1024 / 1024
    return free_space_mb