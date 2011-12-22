import socket
from xml.dom.minidom import parseString

# FIXME: Should we put the string literals (the commands) we send to the server in some kind of structure? This would make it easier to change the messages.

class TIA_client(object):
    """This class provides a client for the TIA network protocol (version 1.0)."""
    
    def __init__(self):
        """Initializes TIA_client object."""
        self.sock = None  # FIXME: Is it better to make sock private, i.e. use self.__sock? Or self._sock?
    
    def connect(self, host, port):
        """Connects to server on host:port."""
        if self.sock != None:  # Socket already exists
            print "Connection already established."  # FIXME: Better way to handle this warning instead of just using print?
            return
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create socket
            
        try:
            self.sock.connect((host, port))  # Connect to host:port
        except socket.error:
            self.sock.close()
            self.sock = None
            print "Error: Cannot establish connection with server."
    
    def close(self):
        """Closes connection to server."""
        if self.sock != None:
            self.sock.close()
            self.sock = None
        else:
            print "Connection already closed."
    
    def check_protocol(self):
        """Returns True if server supports the protocol version implemented by this client."""
        self.sock.sendall("TiA 1.0\nCheckProtocolVersion\n\n")
        tia_version = self.__readmsgline()  # Contains "TiA 1.0\n"
        status = self.__readmsgline()  # Contains "OK" or "Error"
        self.sock.recv(1)
        if status == "OK":
            return True
        else:
            return False
    
    def __readmsgline(self):  # FIXME: Single _ or double __? What's the correct way to mark this function as "private"?
        """Reads one line (until "\n") of the stream."""
        line = ""
        while True:
            msg = self.sock.recv(1)  # Read 1 byte
            if msg == "\n":
                return line
            else:
                line += msg
    
    def get_metainfo(self):
        """Retrieves meta information from the server."""
        self.sock.sendall("TiA 1.0\nGetMetaInfo\n\n")
        
        tia_version = self.__readmsgline()  # Contains "TiA 1.0\n"
        print tia_version
        msg = self.__readmsgline()  # Contains "TiA 1.0\n"  # Contains "MetaInfo\n"
        print msg
        msg = self.__readmsgline()  # Contains "Content-Length:xxx\n", where xxx is the number of bytes that follow
        content_len = int(msg.split(":")[-1])
        print content_len
        msg = self.sock.recv(content_len + 1)  # There is one extra "\n" at the end of the message
        print msg
        dom = parseString(msg)
        # TODO: Parse dom structure, we need a list of signals, each entry containing the signal's attributes (sampling rate, block size, ...)
        #       We also might need other meta information such as subject name and other attributes
        #       The list of signals might be a list of dictionaries, e.g. [{'blocksize': 10, 'sampleRate': 100, 'type': 'eeg', 'numChannels', 4}] for one signal
    
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
    

