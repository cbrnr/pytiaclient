import socket
from lxml import etree

# FIXME: Should we put the string literals (the commands) we send to the server in some kind of structure? This would make it easier to change the messages.

class TIA_client(object):
    """This class provides a client for the TIA network protocol (version 1.0)."""
    
    def __init__(self):
        """Initializes TIA_client object."""
        self._sock = None
        self._metainfo = {"subject": None, "masterSignal": None, "signal": []}
    
    def connect(self, host, port):
        """Connects to server on host:port."""
        if self._sock != None:  # Socket already exists
            print "Connection already established."  # FIXME: Better way to handle this warning instead of just using print?
            return
            
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create socket
            
        try:
            self._sock.connect((host, port))  # Connect to host:port
        except socket.error:
            self._sock.close()
            self._sock = None
            print "Error: Cannot establish connection with server."
    
    def close(self):
        """Closes connection to server."""
        if self._sock != None:
            self._sock.close()
            self._sock = None
        else:
            print "Connection already closed."
    
    def check_protocol(self):
        """Returns True if server supports the protocol version implemented by this client."""
        self._sock.sendall("TiA 1.0\nCheckProtocolVersion\n\n")
        tia_version = self._recv_until()  # Contains "TiA 1.0\n"
        status = self._recv_until()  # Contains "OK" or "Error"
        self._sock.recv(1)
        if status.strip() == "OK":
            return True
        else:
            return False
    
    def get_metainfo(self):
        """Retrieves meta information from the server."""
        self._sock.sendall("TiA 1.0\nGetMetaInfo\n\n")
        
        tia_version = self._recv_until().strip()  # Contains "TiA 1.0\n" (remove trailing "\n")
        msg = self._recv_until().strip()  # Contains "TiA 1.0\n"  # Contains "MetaInfo\n" (remove trailing "\n")
        msg = self._recv_until().strip()  # Contains "Content-Length:xxx\n", where xxx is the number of bytes that follow (remove trailing "\n")
        content_len = int(msg.split(":")[-1])
        xml_string = self._sock.recv(content_len + 1).strip()  # There is one extra "\n" at the end of the message
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
        """Creates a data connection via TCP or UDP."""
        # TODO: Create new socket (TCP or UDP, depending on connection)
    
    def start_data(self):
        """Starts data transmission."""
        # TODO: Start receiving data into buffer
    
    def stop_data(self):
        """Stops data transmission."""
        # TODO: Stop receiving data
    
    def get_state_connection(self):
        """Creates a state connection."""
        # TODO
    
    def _recv_until(self, suffix="\n"):
        """Reads from socket until the character suffix is in the stream."""
        msg = ""
        while not msg.endswith(suffix):
            data = self._sock.recv(1)  # Read a fixed number of bytes
            if not data:
                raise EOFError("Socket closed before receiving the delimiter.".format(suffix))
            msg += data
        return msg


