"""
Script processes Iridium SBD messages that have been saved to files.
Iridium headers are removed, and pure data is saved to new files with the .txt or .bin extensions
Data that has been split over multiple messages is stitched together into a single file

See example at end of file
"""

import os
from pathlib import Path


BYTE_DESCRIPTIONS = {
    0x30: "Self-timed",
    0x31: "Self-timed extended",
    0x32: "Entering alarm",
    0x33: "Entering alarm extended",
    0x34: "Exiting alarm",
    0x35: "Exiting alarm extended",
    0x36: "Command response",
    0x37: "Command response extended",
    0x38: "Forced transmission",
    0x39: "Forced transmission extended",
}

EXTENDED_BYTES = {0x31, 0x33, 0x35, 0x37, 0x39}

CERT_BEGIN = "-----BEGIN DATA CONTENT-----"
CERT_END = "-----END DATA CONTENT-----"

def parse_sbd(path):
    def parse_filename(filename):
        base = os.path.basename(filename)
        name, ext = os.path.splitext(base)
        if ext.lower() != '.sbd':
            print(f"Unsupported file extension '{ext}'. Expected '.sbd'")
        parts = name.split('_')
        if len(parts) == 2:
            imei, momsn_str = parts
        else:
            print(f"Filename '{filename}' does not match the expected format 'IMEI_MOMSN.sbd'")
            imei, momsn_str = "unknown", "unknown"
        if momsn_str.isdigit():
            momsn = int(momsn_str)
        else :
            momsn = 0
        return imei, momsn

    def read_first_byte(filepath):
        with open(filepath, 'rb') as f:
            byte = f.read(1)
            if not byte:
                raise ValueError(f"File '{filepath}' is empty.")
            return byte[0]

    def get_description(byte_value):
        return BYTE_DESCRIPTIONS.get(byte_value, "Unknown message type")

    def is_extended(byte_value):
        return byte_value in EXTENDED_BYTES

    def check_ascii(data_bytes):
        try:
            data_bytes.decode('ascii')
            return True
        except UnicodeDecodeError:
            return False

    def save_data_to_file(output_path, data, as_hex=False):
        if as_hex:
            with open(output_path.with_suffix('.bin'), 'wb') as f:
                f.write(data)
            print(f"Data saved as hexadecimal to '{output_path.with_suffix('.bin')}'")
        else:
            with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
                f.write(f"{CERT_BEGIN}\n")
                f.write(data)
                f.write(f"\n{CERT_END}\n")
            print(f"Data saved as text to '{output_path.with_suffix('.txt')}'")


    def save_data(filepath, imei_l, momsn_l, data_bytes_l):
        has_non_ascii = not check_ascii(data_bytes_l)
        if has_non_ascii:
            data_content = data_bytes_l
        else:
            data_content = data_bytes_l.decode('ascii', errors='replace').strip()

        print(f"IMEI: {imei_l}")
        print(f"MOMSN: {momsn_l}")
        print(f"Byte Value: 0x{byte_value:02X} {chr(int(byte_value))}")
        print(f"Description: {description}")
        print(CERT_BEGIN)
        if has_non_ascii:
            hex_data = data_content.hex().upper()
            print(hex_data)
        else:
            print(data_content)
        print(CERT_END)

        input_path = Path(filepath)
        output_filename = input_path.stem + "_data"
        output_path = input_path.parent / output_filename

        if has_non_ascii:
            save_data_to_file(output_path, data_content, as_hex=True)
        else:
            save_data_to_file(output_path, data_content, as_hex=False)
        print('\n')

    def parse_subheader(subheader_str):
        # expected for first message 1,0,0,357:
        # for subsequent 1,0,318:
        # with an optional N=station name 1,0,0,357,N=station name
        subheader_str = subheader_str.rstrip(':')
        parts = subheader_str.split(',')

        elements = len(parts)
        id_num, start_byte, total_bytes, station_name = 0, 0, 0, ""
        if elements < 3 or elements > 5:
            valid = False
        else:
            valid = True
            index = 0
            # packet_type = parts[0]  # caller already knows
            id_num = int(parts[1])
            start_byte = int(parts[2])
            if start_byte == 0:  # first message has total bytes
                index = 4
                if elements >= 3:
                    total_bytes = int(parts[3])
                else:
                    valid = False
            else:
                total_bytes = 0  # subsequent messages don't have total bytes
                index = 3

            #there may be a station name
            if index < elements:
                name_token = parts[index]
                if name_token.startswith("N="):
                    station_name = name_token[2:]

        return {
            'valid' : valid,
            'id': (id_num),
            'start_byte': (start_byte),
            'total_bytes': (total_bytes),
            'station_name': station_name
        }

    input_path = Path(path)
    if not input_path.exists():
        print(f"Error: The path '{path}' does not exist.")
        return
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.sbd"), key=lambda f: parse_filename(f.name)[1])
    else:
        print(f"Error: The path '{input_path}' is neither a file nor a directory.")
        return

    stat_total_files = 0
    stat_total_good = 0
    stat_total_bad = 0
    stat_extendeds = 0
    stat_singles = 0

    extended_imei = 0
    extended_files_found = 0
    total_bytes_expected, total_bytes_collected = 0, 0
    extended_data_collected = bytearray()
    momsn_list = []
    for file in files:
        stat_total_files += 1

        try:
            imei, momsn = parse_filename(file.name)
        except ValueError as ve:
            print(f"Skipping file '{file}': {ve}")
            stat_total_bad += 1
            continue
        try:
            byte_value = read_first_byte(file)
        except ValueError as ve:
            print(f"Skipping file '{file}': {ve}")
            stat_total_bad += 1
            continue
        description = get_description(byte_value)

        with open(file, 'rb') as f:
            data_bytes = f.read()

        print(f"Parsing file: '{file}', IMEI {imei}, MOMSN {momsn}")

        if is_extended(byte_value):
            stat_extendeds += 1
            error = False

            # let's handle the subheader
            data_str = data_bytes.decode('utf-8', errors='replace')
            colon_index = data_str.find(':')
            if colon_index == -1:
                print(f"Skipping file '{file}': Sub-header not properly terminated.")
                continue
            sub_header_str = data_str[:colon_index+1]
            try:
                sub_header = parse_subheader(sub_header_str)
            except ValueError as ve:
                print(f"Skipping file '{file}': {ve}")
                continue

            # lets get the data form the message
            data_this_msg = data_bytes[colon_index+1:]
            data_len = len(data_this_msg)

            # is this the first message?  or a different imei
            if (sub_header['total_bytes'] > 0) or (extended_imei != imei):
                # this is the first packet
                if extended_files_found > 0:
                    print(f"Error: file {file}, IMEI {imei}, MOMSN {momsn}: Found new header message before completing previous stitch")
                    save_data(str(file), imei, momsn_list, extended_data_collected)
                    error = True

                # first message - clean up any leftovers from previous
                momsn_list.clear()
                extended_imei = imei
                extended_data_collected.clear()
                extended_files_found = 1
                total_bytes_expected = sub_header['total_bytes']
                total_bytes_collected = 0

                print(f"First extended message found: MOMSN {momsn}, total extended bytes {total_bytes_expected}, bytes in this message {data_len}")
            else:
                if extended_files_found == 0:
                    total_bytes_expected = 0  # set to zero to end with this message
                    print(f"Error: file {file}, IMEI {imei}, MOMSN {momsn}: Found subsequent before first extended message")
                    error = True

                extended_files_found += 1
                print(f"Subsequent extended message found: MOMSN {momsn}, message {extended_files_found}, bytes in this message {data_len}")

            # add message data
            momsn_list.append(momsn)
            extended_data_collected += data_this_msg
            total_bytes_collected += data_len

            # did we complete?
            complete = False
            if total_bytes_collected == total_bytes_expected:
                complete = True
                print(f"Success: {extended_files_found} messages, {total_bytes_collected} bytes, stitched together")
                save_data(str(file), imei, momsn_list, extended_data_collected)

            elif total_bytes_collected > total_bytes_expected:
                complete = True
                print(
                    f"Error: file {file}, IMEI {imei}, MOMSN {momsn}: Expected {total_bytes_expected} bytes.  Received {total_bytes_collected}")
                save_data(str(file), imei, momsn_list, extended_data_collected)
                error = True

            if complete:
                momsn_list.clear()
                extended_imei = 0
                extended_data_collected.clear()
                extended_files_found = 0
                total_bytes_expected = sub_header['total_bytes']
                total_bytes_collected = 0

            if error:
                stat_total_bad += 1
            else:
                stat_total_good += 1

        else:
            # not an extended packet
            data_this_msg = data_bytes[1:]
            momsn_list = momsn
            print(f"Success: single messasge, {len(data_this_msg)} bytes")
            save_data(str(file), imei, momsn_list, data_this_msg)

            stat_total_good += 1
            stat_total_files += 1
            stat_singles += 1

    print(f"Complete. total files {stat_total_files}, good files {stat_total_good}, bad files {stat_total_bad}, singles {stat_singles}, extendeds {stat_extendeds}")



#example usage:
parse_sbd('D:/Data/SL3XL2/Iridium/Single/300434061335610_001914.sbd')
parse_sbd('D:/Data/SL3XL2/Iridium/Extended/batch/Crypt')
