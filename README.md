PyTIAclient
===========

PyTIAClient is a Python client for the TOBI Interface A (TIA) protocol, a protocol to transmit measurement data over the network.

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

Project website
---------------

https://github.com/cle1109/pytiaclient

Support
-------

Please let me know if you are having issues with PyTIAClient (for example by creating a new issue or via email).

License
-------

This project is licensed under the GNU GPL (version 3 or higher). Copyright 2014 by [Clemens Brunner](mailto:clemens.brunner@tugraz.at).