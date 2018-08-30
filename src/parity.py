# Example:  demonstrates adding parity bits to a string

def odd(s):
    """
    Convert a byte string in to an odd parity byte string (number of one-bits in each character is odd)

    example::
        parity.odd(b'test')
        b'\xf4\xe5s\xf4

    :param bytes s: String to convert.
    :returns: Same string but with odd parity applied.
    :rtype: bytes
    """

    def odd_byte(c):
        if (sum(bool(c & 1 << bit) for bit in range(8))) & 1:
            return c
        return c | 128

    return bytes(map(odd_byte, s))

def even(s):
    """
    Convert a byte string in to an even parity byte string (number of one-bits in each character is even)

    example::
        parity.even(b'test')
        b'te\xf3t'

    :param bytes s: String to convert.
    :returns: Same string but with even parity applied.
    :rtype: bytes
    """

    def even_byte(c):
        if (sum(bool(c & 1 << bit) for bit in range(8))) & 1:
            return c | 128
        return c

    return bytes(map(even_byte, s))
