=====
Usage
=====

.. note::

    HEYKUBE is still in beta, with lots of work to clean it up. 
    Check the examples directory, or run the command line interface

.. automodule:: heykube

.. code-block:: python
    class heykube():

.. autoclass:: heykube
    :members:

.. autoclass:: Cube
    :members:

.. autoclass:: Match
    :members:


This block shows how to connect to an initial HEYKUBE

.. code-block:: python

    import heykube
    import time
    import random
    
    # Connect to the cube
    cube = heykube.heykube()
    device = cube.get_device()
    
    # If not found, just exit
    if device is None:
        exit()
    
    # Run the connection
    if not cube.connect(device):
        print('Failed to connect with a HEYKUBE')
        exit()
