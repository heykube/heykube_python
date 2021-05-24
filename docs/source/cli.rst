.. highlight:: shell

===
CLI
===

.. note::

    HEYKUBE is still in beta, with lots of work to clean it up. 
    Check the examples directory, or run the command line interface

This code shows how to run the command line interface (CLI) for HEYKUBE

.. code-block:: console

   $ cd scripts
   $ ./heykube_cli.py


The CLI initially scans for HEYKUBEs, and you can connect

.. code-block:: console

    Starting HEYKUBE Command line interface (CLI)
    Scanning for HEYKUBEs
       HEYKUBE-28F1 : addr FC:AE:7C:F7:28:F1 at -56 dB RSSI
    HEYKUBE> connect HEYKUBE-28F1
    HEYKUBE-28F1> check_version
    Software version: v0.99
    BTLE disconnect: Remote User Terminated Connection
    HEYKUBE-28F1> help
   
    Documented commands (type help <topic>):
    ========================================
    check_battery   disconnect        help        prompt_face  write_instructions
    check_version   enable_sounds     hints_off   quit
    connect         get_instructions  hints_on    reset
    debug_level     get_moves         play_sound  scan
    disable_sounds  get_orientation   print_cube  track_cube
   
    HEYKUBE-28F1>

