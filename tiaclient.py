import socket
import threading
from lxml import etree

class TIAClient(object):
    """Provides a client for the TIA network protocol (version 1.0)."""
    
    def __init__(self):
        self._sock = None
        self._metainfo = {"subject": None, "masterSignal": None, "signal": []}
        self._buffer = []
    
    def connect(self, host, port):
        """Connects to server on host:port."""
        if self._sock != None:  # Socket already exists
            raise TIAError("Connection already established.")
        
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create socket
            self._sock.settimeout(2)
            self._sock.connect((host, port))  # Connect to host:port
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
            tia_version = self._recv_until()  # Contains "TiA 1.0\n"
            status = self._recv_until()  # Contains "OK" or "Error"
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("Could not check protocol version.")
        
        if status.strip() == "OK":
            return True
        else:
            return False
    
    def get_metainfo(self):
        """Retrieves meta information from the server."""
        if self._sock == None:
            raise TIAError("No connection established.")
        
        try:
            self._sock.sendall("TiA 1.0\nGetMetaInfo\n\n")
            tia_version = self._recv_until().strip()  # Contains "TiA 1.0\n" (remove trailing "\n")
            msg = self._recv_until().strip()  # Contains "TiA 1.0\n"  # Contains "MetaInfo\n" (remove trailing "\n")
            msg = self._recv_until().strip()  # Contains "Content-Length:xxx\n", where xxx is the number of bytes that follow (remove trailing "\n")
            content_len = int(msg.split(":")[-1])
            xml_string = self._sock.recv(content_len + 1).strip()  # There is one extra "\n" at the end of the message
        except socket.error, EOFError:
            raise TIAError("Could not receive metainfo.")

        xml = etree.fromstring(xml_string)
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
        
    def get_data_connection(self, connection):
        """Creates a data connection via TCP or UDP.
             Input:  connection: "TCP" or "UDP"
             Output: port number of new data connection
        """
        if self._sock == None:
            raise TIAError("No connection established.")
        if connection != "TCP" and connection != "UDP":
            raise TIAError("Connection must be either TCP or UDP.")
        
        try:
            self._sock.sendall("TiA 1.0\nGetDataConnection: " + connection + "\n\n")
            tia_version = self._recv_until()  # Contains "TiA 1.0\n"
            port = self._recv_until()  # Contains "OK" or "Error"
            self._sock.recv(1)
        except socket.error, EOFError:
            raise TIAError("Could not get port of new data connection.")
        
        if port.find("Error -- Target and remote subnet do not match!") != -1:
            raise TIAError("Target and remote subnets do not match for UDP data connection.")
        else:
            return int(port.split(":")[-1].strip())
    
    def start_data(self):
        """Starts data transmission."""
        # TODO: Start receiving data into buffer
        # Calls _get_data_worker, which runs in a new thread and collects data from the
        # socket buffer and writes it into the internal buffer.
        
    
    def stop_data(self):
        """Stops data transmission."""
        # TODO: Stop receiving data
        # Ends _get_data_worker.
    
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
        
    def _get_data(self):
        pass


class TIAError(Exception):
    pass
    
