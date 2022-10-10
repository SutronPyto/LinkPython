def bin6_four(num, count=4, right_digits=0, is_signed=True):
    """
    Converts a number in to a ``count`` byte long 6-bit packed binary string (used for GOES formatting).
    The maximum number of bytes is 4, which allows a representation range of [-8388608 .. 8388607].
    The more ``right_digits`` you request, the smaller the range. For instance with 2 ``right_digits``, the
    the maximum range becomes limited to [-1310.72 .. 1310.71], and even less with fewer bytes.
    
    Examples::
    
        >>> # Convert 1234567 to 6-bit pseudo-binary:
        >>> bin6_four(1234567)
        b'DmZG'
        >>> # Convert 12345 to 6-bit pseudo-binary:
        >>> bin6_four(12345, 3)
        b'C@Y'
        >>> # Convert BV in to a 3-byte 18-bit value:
        >>> BV = 12.32
        >>> bin6_four(BV, 3, 2)
        b'@SP'
        
    :param float num: A number to convert to pseudo-binary format. 
    :param int count: The number of bytes to format (1 to 3).
    :param int right_digits: The number of decimal digits to retain via scaling.
    :param bool is_signed: True if negative values should be allowed.
    :return: A byte string containing 6-bit binary data.
    :rtype: bytes
    """

    # Make sure num bytes is within the allowed range.
    count = max(min(count, 4), 1)

    # Pre-allocate a byte array of the desired length.
    result = bytearray(count)

    max_val = [[63, 4095, 262143, 16777216], [31, 2047, 131071, 8388607]]
    min_val = [[0, 0, 0, 0], [-32, -2048, -131072, -8388608]]
    mask = [0x0000003F, 0x00000FFF, 0x0003FFFF, 0xffffff]

    # Scale and round the value based on the allowed range and number of right digits desired.
    scaled = round(num * 10 ** right_digits)
    scaled = min(scaled, max_val[is_signed][count - 1])
    scaled = max(scaled, min_val[is_signed][count - 1])

    # Format the result.
    for i in range(count):
        cbyte = (scaled & mask[i]) >> (i * 6)
        result[count - i - 1] = 63 if cbyte == 63 else cbyte + 64

    return bytes(result)

print(bin6_four(12345, 3))
BV = 12.32
print(bin6_four(BV, 3, 2))
print(bin6_four(1234567))
      


