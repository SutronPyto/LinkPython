# Example:  demonstrates some simple TX format scripts

from sl3 import *


@TXFORMAT
def append_info(standard):
    """appends information to tx"""
    return standard + " Little Creek A21938"


"""this id is unique to each station"""
unique_id = "A17_BS_128"


@TXFORMAT
def prefix_id_1(standard):
    """prefixes station id"""
    global unique_id
    return unique_id + " " + standard


@TXFORMAT
def prefix_id_2(standard):
    """prefixes station name"""
    station_name = command_line("!STATION NAME\r", 128).strip()
    return station_name + " " + standard


@TXFORMAT
def destroy(standard):
    """destroys standard format"""
    return "kittens ate your data"
