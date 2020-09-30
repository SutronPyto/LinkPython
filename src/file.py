# Example:  Demonstrates file operations
"""

With the addition of an SD card to the system, file operations become useful.
This module provides examples of file operations on the SD card.

Notes

* "SD/" is the root folder for the SD drive.  "SD/TX1" is an example subfolder
* Use forward slash / to separate folders and files e.g. "SD/folder/file.txt"
* FAT32 is the only supported file system
* The system automatically mounts the SD card
* The command line interface supports advanced file operations (please see user manual)
* Files may be transmitted to an FTP server (please see user manual)
* The "SD/TX1", "SD/TX2", etc. folders are used to hold files for transmissions
* Transmitted files are automatically deleted


MicroPython

* MicroPython file operations have some minor differences from Python 3.5
* include uos to use file operations
* use uos.exists() to see if a file exists (there is no uos.path module)
* seek is limited to files under 1GB

"""

from sl3 import *
import uos

def file_demo():
    """

    :return:
    :rtype:
    """

    # create a new file and write some data to it
    f = open('SD/my_file.txt', 'w')
    f.write('here is some data')
    f.close()

    # open the file and read the data from it
    f = open('SD/my_file.txt')
    file_content = f.read()
    print(file_content)
    f.close()

    # append some data to the file
    f = open('SD/my_file.txt', 'a')
    f.write(' and even more data')
    f.close()

    # open the file and read the data from it
    f = open('SD/my_file.txt')
    file_content = f.read()
    print(file_content)
    f.close()

    # list the files in the SD root folder
    file_list = uos.listdir('SD')
    print(file_list)

    # verify the file exists
    file_exists = uos.exists('SD/my_file.txt')
    if file_exists:
        print('found file')
    else:
        print('file missing')

    # remove the file and list again
    uos.remove('SD/my_file.txt')
    file_list = uos.listdir('SD')
    print(file_list)


def format_date(time_t):
    """
    returns a string with the formatted date as YYYY_MM_DD_HH_MM_SS
    """
    # if it is not already, convert time to a tuple as per localtime()
    if type(time_t) is float:
        time_t = utime.localtime(time_t)
    return "{:04d}_{:02d}_{:02d}_{:02d}_{:02d}_{:02d}".format(time_t[0], time_t[1], time_t[2],
                                                              time_t[3], time_t[4], time_t[5])


def unique_file_name(prefix, time_t, ext):
    """
    Creates a unique file name using this pattern:
    prefix_YYYY_MM_DD_HH_MM_SS.ext
    if such a file already exists, appends _xN to file name above,
    where N is an incrementing number, until a unique file name is found

    :return: unique file name
    :rtype: str
    """
    name_base = prefix + "_" + format_date(time_t)

    name = name_base + "." + ext
    if uos.exists(name):
        for i in range(1, 9999):
            name = "{}_x{}.{}".format(name_base, i, ext)
            if not uos.exists(name):
                break
    return name


@TASK
def diagnostic_file_for_tx():
    """
    Creates a diagnostic file and places into the TX1 folder
    """
    # create file name.  include the folder
    folder = "SD/TX1"  # unless file is in correct folder, it will not get transmitted!
    if not uos.exists(folder):  # make sure the folder exists
        uos.mkdir(folder)

    file_prefix = folder + "/" + setup_read("STATION NAME") + "_diag"

    # call routine that will append the time to the file name and make sure it is unique
    file_name = unique_file_name(file_prefix, utime.time(), "txt")
    print(file_name)  # for diagnostics - see via SCRIPT STATUS

    # create file content
    content = command_line("!GET DIAG", 1024 * 8)

    # write content to file
    with open(file_name, "w") as f:
        f.write(content)


