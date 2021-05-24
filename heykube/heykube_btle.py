# ========================================
# Copyright 2021 22nd Solutions, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO 
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
# ========================================
from queue import Queue
import time
import threading
import asyncio
import re
from bleak import BleakClient
from bleak import BleakScanner
import logging
import argparse

# -------------------------------------------------
# -------------------------------------------------
# Defines wireless connectivity 
# -------------------------------------------------
# -------------------------------------------------

# HEYKUBE connectivity class
class heykube_btle():

    client: BleakClient = None

    def __init__(self):
        self.logger = logging.getLogger('heykube_btle')
        self.logger.info('Initializing HEYKUBE BTLE class')

        # Device state
        self.connected = False
        self.connected_device = None

        # Setup multiple queues
        self.cmd_queue = Queue()
        self.read_queue = Queue()
        self.notify_queue = Queue()

        # clear the device
        self.device = None
        self.addr = None

        # Setup device UUID
        self.heykube_uuid = "b46a791a-8273-4fc1-9e67-94d3dc2aac1c"
        self.char_uuid = {'Version' :      '5b9009f6-03bf-41aa-87fc-582d8b2bd6b9',
                          'Battery' :      'fd51b3ba-99c7-49c6-9f85-5644ff56a378',
                          'Config' :       'f0ac8d24-6daf-4f47-9953-fd921da215e1',
                          'CubeState' :    'a2f41a4e-0e31-4bbc-9389-4253475481fb',
                          'Status' :       '9bbc2d67-0ba7-4440-aedf-08fb019687f9',
                          'MatchState' :   '982af399-ef78-4eff-b24d-2e1a01aa9f13',
                          'Instructions' : '1379570d-86c6-45a4-8778-f552e7feb290',
                          'Action' :       'e06da2b8-c643-42b1-895b-a5acbbf30afd',
                          'Accel' :        '272a1fe9-058b-402b-8298-7fec5ce7473e',
                          'Moves' :        'F2FF5401-2BC0-415B-A2F1-6549D6CA0AD8'}

        self.char_handles = {24 : 'Status', 19 : 'CubeState'}

        # set BTLE disconnect reasons
        self.disconnect_reasons = { 0x13 : "Remote User Terminated Connection", 
                                    0x10 : "Connection Accept Timeout Exceeded",
                                    0x08 : "Connection timeout"}


    # ---------------------------------------------------
    # Public interface
    # --------------------------------------------------
    def parse_args(self):

        parser = argparse.ArgumentParser(description='Defines the HEYKUBE connection options')
        parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
        # 4 different options
        parser.add_argument('-n', "--name", action='store', help="Directly defines name of a HEYKUBE for connection", type=str)
        parser.add_argument('-a', "--address", action='store', help="Directly defines an HEYKUBE MAC address for connection", type=str)
        parser.add_argument('-s', "--scan", help="Scans and reports all the available HEYKUBES", action="store_true")
        parser.add_argument('-d', "--debug", action='store_true', help="Turns on debug prints")
        parser.add_argument("--dev-board", action='store_true', help="Turns on the devboard mode with external user input")

        #return parser.parse_args()
        return parser.parse_known_args()

    def scan(self, timeout=5.0):
        """ Scan for HEYKUBE devices """
        # Run the loop for 5 seconds
        scan_loop = asyncio.new_event_loop()
        scan_loop.run_until_complete(self.scan_run())

        return self.scan_devices

    def is_connected(self):
        if self.client:
            return True
        else:
            return False

    def get_device(self, args):

        # Find the device
        connected_device = None

        # Run the scan
        scan_devices = self.scan()

        # Scan for HEYKUBES
        if args.scan or (args.name is None and args.address is None):
            if len(scan_devices) == 0:
                print('Did not find any HEYKUBEs, wakeup them up by moving them')
                print('')
                print('You can check for previously connected devics')
                print('# check for connected devices')
                print('hcitool conn')
                print('')
                print('# disconnect them if needed')
                print('hcitool ledc 64')
            for device in scan_devices:
                print('    {} : addr {} at {} dB RSSI'.format(device.name, device.address, device.rssi))


        # Match name
        if args.name:
            for device in scan_devices:
                if args.name == device.name:
                    connected_device = device
                    break
            if connected_device is None:
                self.logger.warning('Did not find {} - make sure it is close by and turn a face to enable bluetooth'.format(args.name))

        # Match address
        elif args.address:
            for device in scan_devices:
                if args.address == device.address:
                    connected_device = device
                    break
            if connected_device is None:
                self.logger.warning('Did not find {} - make sure it is close by and turn a face to enable bluetooth'.format(args.address))

        # Connect to the first one
        elif not args.scan:
            if len(scan_devices) > 0:
                connected_device = scan_devices[0]


        return connected_device

    def connect(self, device, timeout=10):
        """ Connect to a HEYKUBE """

        # Start the thread to connect
        self.logger.info('Starting thread')
        self.thread = threading.Thread(target=self.connection_thread,args=(device,))
        self.thread.start()

        # Wait for connection
        start_time = time.time()
        while True: 
            if not self.read_queue.empty():
                read_resp = self.read_queue.get()
                #print('read_resp ', read_resp)
                self.logger.info('read_resp {}'.format(read_resp))
                if read_resp[0] == 'connected':
                    return True

            # timeout
            elif (time.time() - start_time) >= timeout:
                self.disconnect()
                while not self.read_queue.empty():
                    self.read_queue.get()
                self.logger.error('Timeout in connection after {} seconds, disconnecting'.format(timeout))
                return False

    def disconnect(self):
        """ Disconnect """

        # send the disconnect command
        self.cmd_queue.put(['disconnect'])

        #print('Waiting for connection thread to finish')
        self.logger.info('Waiting for connection thread to finish')
        self.thread.join()
        self.logger.info('Done with thread')

    def read_cube(self, field):

        # read the characteristics
        start_time = time.time()

        # send the disconnect command
        self.cmd_queue.put(['read', field])

        while True: 
            if not self.read_queue.empty():
                read_resp = self.read_queue.get()
                self.logger.info('read_resp {}'.format(read_resp))
                if read_resp[0] == 'read':
                    return list(read_resp[1])
            elif (time.time() - start_time) >= 5.0:
                self.logger.error('ERROR timeout in cube read')
                return list()

    def write_cube(self, field, data, wait_for_response=True):
        # send the disconnect command
        self.cmd_queue.put(['write', field, data])

    def unsubscribe(self, field):
        """Unscubscribe from notifications"""
        self.cmd_queue.put(['unsubscribe',field])

    def subscribe(self, field):
        """Subscribe to notifications"""
        self.cmd_queue.put(['subscribe',field])

    # ---------------------------------------------------
    # Internal code
    # --------------------------------------------------
    def on_disconnect(self, client: BleakClient):
        self.connected = False
        print('Disconnected from HEYKUBE')

    def connection_thread(self, device):

        # Get a new loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # setup BLEAK client
        self.client = BleakClient(device.address, loop=self.loop)
        self.connected = False
        self.reconnected = False
        self.disconnected = False

        # Launching the connection thread
        tasks = []

        # run the connections manager
        futures = asyncio.gather(self.connection_manager(), self.comms_manager())

        # Run til they are complete
        self.loop.run_until_complete(futures)
        self.logger.info('Closing out the connection')
        self.loop.close()
        
        # Clear the command queue
        while not self.cmd_queue.empty():
            self.cmd_queue.get()


    async def connection_manager(self):

        connection_retries = 0
        first_connection = True

        # ------------------------------------------
        # Keep the connection going
        # ------------------------------------------
        while True:

            # ------------------------------------------------
            # Keep connection running
            # ------------------------------------------------
            if self.disconnected:
                return
            elif self.connected:
                await asyncio.sleep(0.1,loop=self.loop)
            # ------------------------------------------------
            # Bail-out for disconnect
            # ------------------------------------------------
            #elif self.client is None:
            #    return
            # -------------------------------------------------
            # Keep establishing the connection
            # -------------------------------------------------
            else:
                try:
                    # get the connection
                    await self.client.connect()
                    #self.connected = await self.client.is_connected()
                    self.connected = self.client.is_connected

                    # Check if connected
                    if self.connected:
                        self.logger.info('Connected to {}'.format(self.client))
                        connection_retries = 0
                        self.client.set_disconnected_callback(self.on_disconnect)

                        # First connection 
                        if first_connection:
                            self.read_queue.put(['connected'])
                            first_connection = False
                        else:
                            self.reconnected = True
                    else:
                        connection_retries += 1
                        self.logger.error('Failed to connect to {}'.format(self.client))
                except Exception as e:
                    #self.logger.error('connection_manager exception: {}'.format(e))
                    self.logger.error('Trying to reconnect to HEYKUBE')

                if connection_retries >= 3:
                    self.logger.error('connection_manager exception: {}'.format(e))
                    return

    async def comms_manager(self):
        

        num_tries = 0
        cmd = [None, None]
        notify_list = list()
        
        # -------------------------------------------------
        # Run the connection
        # -------------------------------------------------
        while True:

            # Run theh command
            if self.connected:

                # Check if we get a new command
                if cmd[0] is None:
                    if not self.cmd_queue.empty():
                        cmd = self.cmd_queue.get()
                        self.logger.info('Testing {}'.format(cmd))
                        num_tries += 1

                # -------------------------------------
                # Reconnect subscription
                # -------------------------------------
                if self.reconnected:
                    for UUID in notify_list:
                        try:
                            await self.client.start_notify(UUID, self.notification_handler)
                            self.reconnected = False
                        except Exception as e:
                            self.logger.exception('comms_manager::resubscribe Failure')
                            print(e)

                # -------------------------------------
                # Disconnect 
                # -------------------------------------
                if cmd[0] == 'disconnect':
                    self.disconnected = True
                    await self.client.disconnect()
                    self.client = None
                    self.logger.info('Done with disconnect')
                    return

                # -------------------------------------
                # Read characteristics
                # -------------------------------------
                elif cmd[0] == 'read':
            
                    UUID = self.char_uuid[cmd[1]]
                    self.logger.info('Reading from {}'.format(cmd[1]))

                    read_bytes = list()
                    try:
                        read_bytes = await self.client.read_gatt_char(UUID)

                        # success
                        if len(read_bytes) > 0:
                            cmd[0] = None
                            num_tries = 0
                            self.logger.info('Sending bytes {}'.format(read_bytes))
                            self.read_queue.put(['read', read_bytes])
                        else:
                            self.logger.error('WHY AM I HERE -- Read did not fail correctly')

                    except Exception as e:
                        self.logger.exception('comms_manager::Read Failure')
                        print(e)
                # -------------------------------------
                # Write characteristics
                # -------------------------------------
                elif cmd[0] == 'write':
                            
                    # Setup data
                    UUID = self.char_uuid[cmd[1]]
                    bytes_to_send = bytearray(cmd[2])
            
                    self.logger.info('Writing to {}'.format(cmd[1]))
                    try:
                        response = False
                        await self.client.write_gatt_char(UUID, bytes_to_send, response=response)
                        cmd[0] = None
                        num_tries = 0
                        if response:
                            self.logger.info('Done with write')
                    except Exception as e:
                        self.logger.exception('comms_manager::Write Failure')
                        print(e)

                # -------------------------------------
                # Subscribe to characteristics
                # -------------------------------------
                elif cmd[0] == 'subscribe':
                    UUID = self.char_uuid[cmd[1]]

                    if UUID in notify_list:
                        self.logger.warning('Already subscribed to {}'.format(cmd[1]))
                        num_tries = 0
                        cmd[0] = None
                    else:
                        try:
                            await self.client.start_notify(UUID, self.notification_handler)
                            num_tries = 0
                            cmd[0] = None
                            notify_list.append(UUID)
                        except Exception as e:
                            self.logger.error('subscribe Failure with {}'.format(e))

                # -------------------------------------
                # Unsubscribe if written
                # -------------------------------------
                elif cmd[0] == 'unsubscribe':
                    UUID = self.char_uuid[cmd[1]]

                    # handle unsubcribe
                    if UUID in notify_list:
                        try:
                            self.logger.info('unsubscribe from {}'.format(cmd[1]))
                            await self.client.stop_notify(UUID)
                            num_tries = 0
                            cmd[0] = None
                            notify_list.remove(UUID)
                        except Exception as e:
                            self.logger.exception('comms_manager::unsubscribe Failure')
                            print(e)
                    # ignore the command
                    else:
                        num_tries = 0
                        cmd[0] = None
            
                # ------------------------------------
                # wait for next command
                # ------------------------------------
                else:
                    await asyncio.sleep(0.1,loop=self.loop)

            # ------------------------------------
            # wait for reconnection
            # ------------------------------------
            else:
                await asyncio.sleep(0.1,loop=self.loop)

    async def cleanup(self):
        self.logger.info('Cleaning up')
        if self.client:
            await self.client.disconnect()

    async def scan_run(self):

        # Clear previous devices
        self.scan_devices = list()

        all_devices = await BleakScanner.discover()
        for d in all_devices:
            if 'HEYKUBE' in d.name:
                #print('Found {}({}) at {} dB RSSI'.format(d.name, d.address, d.rssi))
                self.logger.info('Found {}({}) at {} dB RSSI'.format(d.name, d.address, d.rssi))
                self.scan_devices.append(d)

    def notification_handler(self, sender: str, data):

        try:
            self.logger.info('Notification from {}'.format(sender))

            # Handle both int and characteristics list
            sender_id = 0
            if isinstance(sender, int):
                sender_id = sender
            else:
                m = re.search('service000c\/char([0-9A-Fa-f]+)', sender)
                if m:
                    sender_id = int(m.group(1),16)
                    self.logger.info('Convert notification to {}'.format(sender_id))

            #if sender == 20 or sender == 19:
            if sender_id in self.char_handles:
                field = self.char_handles[sender_id]
                self.notify_queue.put([field, list(data)])

        except:
            self.logger.exception('Bad notification from {}'.format(sender))
                
