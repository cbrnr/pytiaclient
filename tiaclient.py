import socket
import threading
import struct
from lxml import etree

# TODO: Queries to server and deconding replies should be outsourced into function.

class TIAClient(object):
    """Client for the TIA network protocol (version 1.0)."""
    
    def __init__(self):
        self._sock = None
        self._sock_data = None
        self._metainfo = {"subject": None, "masterSignal": None, "signal": []}
        self._thread_running = False  # State of the data thread
        self._buffer = []
    
    def connect(self, host, port):
        """Connects to server on host:port."""
        if self._sock != None:
            raise TIAError("Connection already established.")
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(2)
            self._sock.connect((host, port))
        except socket.error:
            self._sock = None
            raise TIAError("Cannot establish connection with server.")
    
    def close(self):
        """Closes connection to server."""
        if self._sock != None:
            self._sock.close()  # TODO: Put a try/except statement around socket.close()?
            self._sock = None
        else:
            raise TIAError("Connection already closed.")
    
    def check_protocol(self):
        """Returns True if server supports the protocol version implemented by this client."""
        if self._sock == None:
            raise TIAError("No connection established.")
        try:
            self._sock.sendall("TiA 1.0\nCheckProtocolVersion\n\n")
            tia_version = self._recv_until().strip()  # Contains "TiA 1.0"
            status = self._recv_until().strip()  # Contains "OK" or "Error"
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("Checking protocol version failed.")
        if status == "OK":  # FIXME: Maybe raising an exception is better than returning a value here?
            return True
        else:
            return False
    
    def get_metainfo(self):
        """Retrieves meta information from the server."""
        if self._sock == None:
            raise TIAError("No connection established.")
        try:
            self._sock.sendall("TiA 1.0\nGetMetaInfo\n\n")
            tia_version = self._recv_until().strip()  # Contains "TiA 1.0"
            msg = self._recv_until().strip()  # Contains "MetaInfo"
            msg = self._recv_until().strip()  # Contains "Content-Length:xxx", where "xxx" is the number of bytes that follow
            content_len = int(msg.split(":")[-1])
            xml_string = self._sock.recv(content_len + 1).strip()  # There is one extra "\n" at the end of the message
        except socket.error, EOFError:
            raise TIAError("Receiving metainfo failed.")
        try:
            xml = etree.fromstring(xml_string)
        except XMLSyntaxError:
            raise TIAError("Could not parse XML metainfo because of syntax error.")
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
    
    def start_data(self, connection="TCP"):
        """Starts data transmission."""
        if self._sock == None:
            raise TIAError("No connection established.")
        if self._sock_data != None:
            raise TIAError("Data connection already established.")
        try:
            port = self._get_data_connection("TCP")  # TODO: For now, only TCP data connections are supported
            self._sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_data.settimeout(2)
            self._sock_data.connect((self._sock.getpeername()[0], port))  # Connect to same host, but new port
        except socket.error:
            self._sock_data = None
            raise TIAError("Cannot establish data connection.")
        self._thread_running = True
        try:
            self._sock.sendall("TiA 1.0\nStartDataTransmission\n\n")
            tia_version = self._recv_until().strip()  # Contains "TiA 1.0"
            status = self._recv_until().strip()  # Contains "OK" or "Error"
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("Starting data transmission failed.")
        if status != "OK":  # FIXME: Maybe raising an exception is better than returning a value here?
            raise TIAError("Starting data transmission failed.")
        #t = threading.Thread(target=self._get_data)
        #t.start()
        data = self._get_data()
    
    def stop_data(self):
        """Stops data transmission."""
        self._thread_running = False
        self._sock_data.close()
        self._sock_data = None
    
    def get_state_connection(self):
        """Creates a state connection."""
        # TODO
        
    def get_data_chunk(self):
        # Returns the internal buffer.
        pass

    def _recv_until(self, suffix="\n"):
        """Reads from socket until the character suffix is in the stream."""
        msg = ""
        while not msg.endswith(suffix):
            data = self._sock.recv(1)  # Read a fixed number of bytes
            if not data:
                raise EOFError("Socket closed before receiving the delimiter.")
            msg += data
        return msg

    def _get_data_connection(self, connection):
        """Returns the port number of the new data connection."""
        if connection != "TCP" and connection != "UDP":
            raise TIAError("Data connection must be either TCP or UDP.")
        try:
            self._sock.sendall("TiA 1.0\nGetDataConnection: " + connection + "\n\n")
            tia_version = self._recv_until().strip()  # Contains "TiA 1.0"
            port = self._recv_until().strip()
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("Could not get port of new data connection.")

        if port.find("Error -- Target and remote subnet do not match!") != -1:
            raise TIAError("Target and remote subnets do not match for UDP data connection.")
        else:
            return int(port.split(":")[-1])

    def _get_data(self):
        print "Thread starting..."
        while self._thread_running:
            # TODO: Get all available data from socket and write it into self._buffer
            (d_version, d_size, d_flags, d_id, d_number, d_timestamp) = struct.unpack("<BIIQQQ", self._sock_data.recv(33))
            
            break
        print "Thread ending..."
        return data
        

class TIAError(Exception):
    pass
    

if __name__ == "__main__":
    client = TIAClient()
    client.connect("137.110.244.73", 9000)
    client.start_data()
    client.stop_data()
    client.close()