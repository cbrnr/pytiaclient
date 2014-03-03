PyTIAclient
===========

PyTIAClient is a client for the TOBI Interface A (TIA) protocol, a protocol to transmit measurement data over the network.

Features
--------

- Implemented in pure Python
- Multi-threaded
- Uses only features from the standard library

Installation
------------

TO DO

Example
-------

    import pytiaclient

    client = pytiaclient.TIAClient()
    client.connect("localhost", 9000)  # assumes that a TIA server is running on localhost:9000
    print(client._metainfo)
    client.start_data()
    input("Press Enter to quit.")
    data = client.get_data_chunk_waiting()
    client.stop_data()
    client.close()

Contribute
----------

- Project website: https://sourceforge.net/projects/pytiaclient/
- Issue tracker: https://sourceforge.net/p/pytiaclient/tickets/
- Source code: http://hg.code.sf.net/p/pytiaclient/code

Support
-------

Please let me know if you are having issues with PyTIAClient (for example by creating a new ticket).

License
-------

This project is licensed under the GNU GPL version 3.