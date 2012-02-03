import socket
import threading
import struct
from lxml import etree

SOCKET_TIMEOUT = 2  # Socket timeout (in seconds)
TIA_VERSION = 1.0

class TIAClient(object):
    """Client for the TIA network protocol (version 1.0)."""

    def __init__(self):
        self._sock = None
        self._sock_data = None
        self._metainfo = {"subject": None, "masterSignal": None, "signal": []}
        self._thread_running = False
        self._buffer = []
    
    def connect(self, host, port):
        """Connects to server on host:port and establishes control connection."""
        if self._sock != None:
            raise TIAError("connect(): Control connection already established.")
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(SOCKET_TIMEOUT)
            self._sock.connect((host, port))
        except socket.error:
            self._sock = None
            raise TIAError("connect(): Cannot establish control connection (server might be down).")
        if not self._check_protocol():  # Check if protocol is supported by server
            raise TIAError("connect(): Protocol version {} not supported by server.".format(TIA_VERSION))
        self._get_metainfo()  # Get meta information
    
    def close(self):
        """Closes control connection to server."""
        if self._sock_data != None:
            self.stop_data()
        if self._sock != None:
            self._sock.close()  # TODO: Put a try/except statement around socket.close()?
            self._sock = None
        else:
            raise TIAError("close(): Control connection already closed.")
    
    def start_data(self, connection="TCP"):
        """Starts data transmission using TCP or UDP."""
        if self._sock == None:
            raise TIAError("start_data(): Control connection to server not established.")
        if self._sock_data != None:
            raise TIAError("start_data(): Data connection already established.")
        try:
            port = self._get_data_connection("TCP")
            self._sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_data.settimeout(2)
            self._sock_data.connect((self._sock.getpeername()[0], port))  # Connect to same host, but new port
        except socket.error:
            self._sock_data = None
            raise TIAError("start_data(): Cannot establish data connection.")
        self._thread_running = True
        try:
            self._sock.sendall("TiA {}\nStartDataTransmission\n\n".format(TIA_VERSION))
            tia_version = self._recv_until().strip()
            status = self._recv_until().strip()
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("start_data(): Starting data transmission failed.")
        if status != "OK":
            raise TIAError("start_data(): Starting data transmission failed.")
        #t = threading.Thread(target=self._get_data)
        #t.start()
        data = self._get_data()  # FIXME: This replaces the thread, just for debugging purposes
    
    def stop_data(self):
        """Stops data transmission."""
        self._thread_running = False
        if self._sock == None:
            raise TIAError("stop_data(): Control connection to server not established.")
        if self._sock_data == None:
            raise TIAError("stop_data(): No data connection established.")
        try:
            self._sock.sendall("TiA {}\nStopDataTransmission\n\n".format(TIA_VERSION))
            tia_version = self._recv_until().strip()
            status = self._recv_until().strip()
            print status
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("stop_data(): Stopping data transmission failed.")
        self._sock_data.close()
        self._sock_data = None
    
    def get_data_chunk(self):
        """Returns the data buffer and clears it."""
        pass

    def get_state_connection(self):
        """Creates a state connection."""
        # TODO: This method should probably be private. It should run in a separate thread and just receives state messages.

    def _check_protocol(self):
        """Returns True if server supports the protocol version implemented by this client."""
        try:
            self._sock.sendall("TiA {}\nCheckProtocolVersion\n\n".format(TIA_VERSION))
            tia_version = self._recv_until().strip()
            status = self._recv_until().strip()
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("_check_protocol(): Checking protocol version failed (server might be down).")
        return status == "OK"
    
    def _get_metainfo(self):
        """Retrieves meta information from the server."""
        try:
            self._sock.sendall("TiA {}\nGetMetaInfo\n\n".format(TIA_VERSION))
            tia_version = self._recv_until().strip()
            msg = self._recv_until().strip()
            msg = self._recv_until().strip()  # Contains "Content-Length:xxx", where "xxx" is the number of bytes that follow
            content_len = int(msg.split(":")[-1])
            xml_string = self._sock.recv(content_len + 1).strip()  # There is one extra "\n" at the end of the message
        except socket.error, EOFError:
            raise TIAError("_get_metainfo(): Receiving meta information failed (server might be down).")
        try:
            xml = etree.fromstring(xml_string)
        except XMLSyntaxError:
            raise TIAError("_get_metainfo(): Error while parsing XML meta information (syntax error).")
        self._metainfo = {"subject": None, "masterSignal": None, "signal": []}
        if xml.find("subject") is not None:
            self._metainfo["subject"] = dict(xml.find("subject").attrib)
        if xml.find("masterSignal") is not None:
            self._metainfo["masterSignal"] = dict(xml.find("masterSignal").attrib)
        for index, signal in enumerate(xml.findall("signal")):
            self._metainfo["signal"].append(dict(signal.attrib))
            self._metainfo["signal"][index]["channels"] = []  # List of channels
            for channel in signal.findall("channel"):
                self._metainfo["signal"][index]["channels"].append(channel.attrib)

    def _recv_until(self, suffix="\n"):
        """Reads from socket until the character suffix is in the stream."""
        msg = ""
        while not msg.endswith(suffix):
            data = self._sock.recv(1)  # Read a fixed number of bytes
            if not data:
                raise EOFError("_recv_until(): Socket closed before receiving the delimiter.")
            msg += data
        return msg

    def _get_data_connection(self, connection):
        """Returns the port number of the new data connection."""
        if connection != "TCP" and connection != "UDP":
            raise TIAError("Data connection must be either TCP or UDP.")
        try:
            self._sock.sendall("TiA {}\nGetDataConnection: ".format(TIA_VERSION) + connection + "\n\n")
            tia_version = self._recv_until().strip()
            port = self._recv_until().strip()
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("_get_data_connection(): Could not get port of new data connection.")
        if port.find("Error -- Target and remote subnet do not match!") != -1:
            raise TIAError("_get_data_connection(): Target and remote subnets do not match for a UDP data connection.")
        else:
            return int(port.split(":")[-1])

    def _get_data(self):
        print "Thread starting..."
        while self._thread_running:
            # TODO: Get all available data from socket and write it into self._buffer
            (d_version, d_size, d_flags, d_id, d_number, d_timestamp) = struct.unpack("<BIIQQQ", self._sock_data.recv(33))
            n_signals = bin(d_flags).count("1")
            
            break
                
        print "Thread ending..."
        return 1


class TIAError(Exception):
    pass
    

if __name__ == "__main__":
    client = TIAClient()
    client.connect("137.110.244.73", 9000)
    client.start_data()
    client.stop_data()
    client.start_data()
    client.close()
