import math


def recv_until(sock, suffix="\n".encode("ascii")):
    """Reads from socket until the character suffix is in the stream."""
    msg = b""
    while not msg.endswith(suffix):
        data = sock.recv(1)  # Read a fixed number of bytes
        if not data:
            raise EOFError("Socket closed before receiving the delimiter.")
        msg += data
    return msg


def bitcount(number):
    """Counts the number of high bits in number and returns their integer values in a list."""
    high_bits = []
    if number > 0:
        for mask in range(int(math.ceil(math.log(number, 2))) + 1):
            if number & int(math.pow(2, mask)):
                high_bits.append(mask)
    return high_bits
