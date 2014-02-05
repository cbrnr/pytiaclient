#!/usr/bin/env python2

# Copyright 2013 by Clemens Brunner.

# This file is part of Pytiaclient.
#
# Pytiaclient is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pytiaclient is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pytiaclient. If not, see <http://www.gnu.org/licenses/>.


import socket
import threading
import struct
import math
import xml.etree.ElementTree as ElementTree

# TODO: Include logger
# TODO: Include unit tests?

SOCKET_TIMEOUT = 2  # Socket timeout (in seconds)
TIA_VERSION = 1.0
FIXED_HEADER_SIZE = 33  # Fixed header size (in bytes)
BUFFER_SIZE = 2  # Buffer size (in MB)
SIGNAL_TYPES = {"eeg": 0, "emg": 1, "eog": 2, "ecg": 3, "hr": 4, "bp": 5, "button": 6,
                "axes": 7, "sensor": 8, "nirs": 9, "fmri": 10, "keycode": 11,
                "user1": 16, "user2": 17, "user3": 18, "user4": 19,
                "undefined": 20, "event": 21}


class TIAClient(object):
    """Client for the TIA network protocol."""

    def __init__(self):
        self._sock_ctrl = None  # Socket for control connection
        self._sock_data = None  # Socket for data connection
        self._metainfo = {"subject": None, "masterSignal": None, "signals": []}
        self._thread_running = False  # Indicates if data thread is running
        self._data_thread = None
        self._buffer_lock = None
        self._buffer_avail = None
        self._buffer_type = []
        self._buffer_empty = True

    def connect(self, host, port):
        """Connects to server on host:port and establishes control connection."""
        if self._sock_ctrl is not None:
            raise TIAError("Control connection already established.")
        try:
            self._sock_ctrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_ctrl.settimeout(SOCKET_TIMEOUT)
            self._sock_ctrl.connect((host, port))
        except socket.error:
            self._sock_ctrl = None
            raise TIAError("Cannot establish control connection (server might be down).")
        if not self._check_protocol():  # Check if protocol is supported by server
            raise TIAError("Protocol version {} not supported by server.".format(TIA_VERSION))
        self._get_metainfo()

    def close(self):
        """Closes control connection to server."""
        if self._sock_data is not None:  # Stop data transmission (if running)
            self.stop_data()
        if self._sock_ctrl is not None:
            self._sock_ctrl.close()
            self._sock_ctrl = None
        else:
            raise TIAError("Control connection already closed.")

    def start_data(self, connection="TCP"):
        """Starts data transmission using TCP or UDP."""
        if self._sock_ctrl is None:
            raise TIAError("Control connection to server not established.")
        if self._sock_data is not None:
            raise TIAError("Data connection already established.")
        try:
            port = self._get_data_connection("TCP")
            self._sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_data.settimeout(SOCKET_TIMEOUT)
            self._sock_data.connect((self._sock_ctrl.getpeername()[0], port))  # Connect to same host, but new port
        except socket.error:
            self._sock_data = None
            raise TIAError("Cannot establish data connection.")
        try:
            self._sock_ctrl.sendall("TiA {}\nStartDataTransmission\n\n".format(TIA_VERSION).encode("ascii"))
            tia_version = recv_until(self._sock_ctrl).strip()
            status = recv_until(self._sock_ctrl).strip()
            self._sock_ctrl.recv(1)
        except (socket.error, EOFError):
            raise TIAError("Starting data transmission failed.")
        if status != b"OK":
            raise TIAError("Starting data transmission failed.")
        self._clear_buffer()
        self._thread_running = True
        self._data_thread = threading.Thread(target=self._get_data)
        self._buffer_lock = threading.RLock()
        self._buffer_avail = threading.Condition(self._buffer_lock)
        self._data_thread.start()

    def stop_data(self):
        """Stops data transmission."""
        if self._thread_running:
            self._thread_running = False  # The data socket is closed in _get_data() when the thread terminates
            self._data_thread.join()

    def get_data_chunk(self):
        """Returns the data buffer and clears it."""

        with self._buffer_lock:
            tmp = self._buffer
            self._clear_buffer()
            return tmp

    def get_data_chunk_waiting(self):
        """Returns the data buffer and clears it (waits/blocks until data becomes available)."""

        if not self._thread_running:
            raise TIAError("Data transmission has not been started.")

        with self._buffer_lock:
            while self._buffer_empty:
                self._buffer_avail.wait()
            tmp = self._buffer
            self._clear_buffer()
            return tmp

    def get_state_connection(self):
        """Creates a state connection."""
        pass
        # TODO: This method should probably be private, run in a separate thread and just receive state messages.

    def _check_protocol(self):
        """Returns True if server supports the protocol version implemented by this client."""
        try:
            self._sock_ctrl.sendall("TiA {}\nCheckProtocolVersion\n\n".format(TIA_VERSION).encode("ascii"))
            tia_version = recv_until(self._sock_ctrl).strip()
            status = recv_until(self._sock_ctrl).strip()
            self._sock_ctrl.recv(1)
        except (socket.error, EOFError):
            raise TIAError("Checking protocol version failed (server might be down).")
        return status == b"OK"

    def _get_metainfo(self):
        """Retrieves meta information from the server."""
        try:
            self._sock_ctrl.sendall("TiA {}\nGetMetaInfo\n\n".format(TIA_VERSION).encode("ascii"))
            tia_version = recv_until(self._sock_ctrl).strip()
            msg = recv_until(self._sock_ctrl).strip()
            msg = recv_until(
                self._sock_ctrl).strip()  # Contains "Content-Length:xxx", where "xxx" is the number of bytes
            content_len = int(msg.split(b":")[-1])
            xml_string = self._sock_ctrl.recv(
                content_len + 1).strip()  # There is one extra "\n" at the end of the message
        except (socket.error, EOFError):
            raise TIAError("Receiving meta information failed (server might be down).")
        try:
            xml = ElementTree.fromstring(xml_string)
        except ElementTree.ParseError:
            raise TIAError("Error while parsing XML meta information (syntax error).")
        if xml.find("subject") is not None:
            self._metainfo["subject"] = dict(xml.find("subject").attrib)
        if xml.find("masterSignal") is not None:
            self._metainfo["masterSignal"] = dict(xml.find("masterSignal").attrib)
        for index, signal in enumerate(xml.findall("signal")):
            self._metainfo["signals"].append(dict(signal.attrib))
            self._metainfo["signals"][index]["channels"] = []  # List of channels
            for channel in signal.findall("channel"):
                self._metainfo["signals"][index]["channels"].append(
                    channel.attrib)  # TODO: Check if conversion to dict() would make sense

        self._buffer_type = []
        for index, signal in enumerate(self._metainfo["signals"]):
            try:
                self._buffer_type.append(
                    SIGNAL_TYPES[signal["type"]])  # Assign corresponding signal type to each signal group
            except KeyError:
                raise TIAError("Unknown signal type found.")

    def _get_data_connection(self, connection):
        """Returns the port number of the new data connection."""
        if connection != "TCP" and connection != "UDP":
            raise TIAError("Data connection must be either TCP or UDP.")
        try:
            self._sock_ctrl.sendall(
                ("TiA {}\nGetDataConnection: ".format(TIA_VERSION) + connection + "\n\n").encode("ascii"))
            tia_version = recv_until(self._sock_ctrl).strip()
            port = recv_until(self._sock_ctrl).strip()
            self._sock_ctrl.recv(1)
        except (socket.error, EOFError):
            raise TIAError("Could not get port of new data connection.")
        if port.find(b"Error -- Target and remote subnet do not match!") != -1:
            raise TIAError("Target and remote subnets do not match for a UDP data connection.")
        else:
            return int(port.split(b":")[-1])

    def _get_data(self):
        while self._thread_running:
            d_version, d_size, d_flags, d_id, d_number, d_timestamp = struct.unpack("<BIIQQQ", self._sock_data.recv(
                FIXED_HEADER_SIZE))  # Get fixed header
            signal_types = bit_count(d_flags)  # Lists the signal types present in the data packet
            signal_list = [self._buffer_type.index(k) for k in signal_types]  # Indices into the buffer

            n_signals = len(signal_list)
            var_header_size = 4 * n_signals

            # FIXME: I don't know if these values are needed at all; I could just skip over the variable header
            # FIXME: After all, these values are available in the meta information!
            n_channels = []
            block_size = []
            for signals in range(n_signals):
                tmp = struct.unpack("<H", self._sock_data.recv(2))
                n_channels.append(tmp[0])
            for signals in range(n_signals):
                tmp = struct.unpack("<H", self._sock_data.recv(2))
                block_size.append(tmp[0])

            with self._buffer_lock:
                for index, signal in enumerate(signal_list):  # Read signal blocks; signal is the index into the buffer
                    for channel in range(n_channels[index]):
                        for sample in range(block_size[index]):
                            data = struct.unpack("<f", self._sock_data.recv(4))[0]
                            self._buffer[signal][channel].append(data)
                self._buffer_empty = False
                self._buffer_avail.notify_all()

                # TODO: Check for size of self._buffer and delete oldest sample if buffer is too big

        # Stop data transmission        
        try:
            self._sock_ctrl.sendall("TiA {}\nStopDataTransmission\n\n".format(TIA_VERSION).encode("ascii"))
            tia_version = recv_until(self._sock_ctrl).strip()
            status = recv_until(self._sock_ctrl).strip()
            self._sock_ctrl.recv(1)
        except (socket.error, EOFError):
            raise TIAError("Stopping data transmission failed.")
        self._sock_data.close()
        self._sock_data = None

    def _clear_buffer(self):
        """Initializes an empty buffer. Requires metainfo to be read first."""
        # Each signal group is a list entry, so the first signal group is in self._buffer[0]
        # Each signal group is also a list of channels, and each channel is a list of samples
        self._buffer_empty = True
        self._buffer = [[] for _ in range(len(self._metainfo["signals"]))]  # Empty list for each signal group
        for index, signal in enumerate(self._metainfo["signals"]):
            self._buffer[index] = [[] for _ in range(int(signal["numChannels"]))]  # Empty list for each channel


class TIAError(Exception):
    pass


# Helper functions
# TODO: maybe outsource helper functions to separate .py file
def recv_until(sock, suffix="\n".encode("ascii")):
    """Reads from socket until the character suffix is in the stream."""
    msg = b""
    while not msg.endswith(suffix):
        data = sock.recv(1)  # Read a fixed number of bytes
        if not data:
            raise EOFError("Socket closed before receiving the delimiter.")
        msg += data
    return msg


def bit_count(number):
    """Counts the number of high bits in number and returns their integer values in a list."""
    high_bits = []
    if number > 0:
        for mask in range(int(math.ceil(math.log(number, 2))) + 1):
            if number & int(math.pow(2, mask)):
                high_bits.append(mask)
    return high_bits


if __name__ == "__main__":
    client = TIAClient()
    client.connect("129.27.145.32", 9000)
    print(client._metainfo)
    client.start_data()
    input("Press Enter to quit.")
    data = client.get_data_chunk_waiting()
    client.stop_data()
    client.close()
