#!/usr/bin/env python3
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
import heykube
import cmd
import time
import random
import logging
import argparse
import glob

# Setup logger
logging.basicConfig()
logger = logging.getLogger('heykube_cli')


# ------------------------------------------------
# Main Command line interface for HEYKUBE
# ------------------------------------------------
class heykube_cli(cmd.Cmd):

    def __init__(self):

        cmd.Cmd.__init__(self)
        self.cube = heykube.heykube()
        self.connection = self.cube.connectivity

        # Scan for BTLE devices
        self.run_scan()

        self.connected = False
        self.set_prompt()

    def set_prompt(self, name=''):
        if self.connected:
            self.prompt = '{}> '.format(name)
        else:
            self.prompt = 'HEYKUBE> '

    # ----------------------------------------------------
    # Helper functions for the CLI
    # ----------------------------------------------------
    def check_connected(self):
        if self.connected:
            return True
        else:
            logger.warning('Not connected to a HEYKUBE, please connect')
            return False

    def run_scan(self):
        print('Scanning for HEYKUBEs')
        self.scan_devices = self.connection.scan()

        if len(self.scan_devices) == 0:
            print('Did not find any HEYKUBEs. Turn one of the faces to enable the Bluetooth connection')
        for device in self.scan_devices:
            print('    {} : addr {} at {} dB RSSI'.format(device.name, device.address, device.rssi))

    def register_disconnect(self):
        self.connected = False
        self.set_prompt()

    # ----------------------------------------------------
    # CLI commands
    # ----------------------------------------------------
    def do_disconnect(self, arg):
        """
Disconnect from the current HEYKUBE
"""

        logger.info('Disconnecting from HEYKUBE')
        self.connection.disconnect()
        self.register_disconnect()

    def connect_function(self, args):

        # Get the scanned devices
        connect_device = None
        for device in self.scan_devices:
            if args == device.name:
                connect_device = device

        # run the connection
        if connect_device:
            if self.connection.connect(connect_device):
               self.connected = True
               self.set_prompt(connect_device.name)
            else:
               logger.error('Failed to connect to {}({})'.format(connect_device.name, connect_device.address))
        else:
            logger.info('Please pick a HEYKUBE to connect')

    def do_connect(self, args):
        """
Connect to a HEYKUBE. Run scan to find available HEYKUBEs
usage: connect HEYKUBE-XXXX

HEYKUBE> scan
Scanning for HEYKUBEs
    HEYKUBE-28F1 : addr FC:AE:7C:F7:28:F1 at -46 dB RSSI
HEYKUBE> connect HEYKUBE-28F1
HEYKUBE-28F1>
"""

        # update the scan
        if len(self.scan_devices) == 0:
            print('Run scan to find devices')
        else:
            self.connect_function(args)

    def complete_connect(self, text, line, begidx, endidx):
        completions = list()
        device_list = list()

        for device in self.scan_devices:
            device_list.append(device.name)

        if not text:    
            completions = device_list
        else:
            completions = [f for f in device_list if f.startswith(text) ]

        return completions

    def do_scan(self,arg):
        """
Scan for available HEYKUBEs
"""
        self.run_scan()

    def complete_prompt_face(self, text, line, begidx, endidx):
        return ['U', 'L', 'F', 'R', 'B', 'D']

    def do_prompt_face(self, args):
        """
Prompts the lights to flash on a particular face
usage: prompt_face [U | L | F | R | B | D]
"""
        index = 6
        color_set = ['U', 'L', 'F', 'R', 'B', 'D']
        for loop1, val in enumerate(color_set):
            if args == val: 
                index = loop1                        
                break

        if index < 6:
            self.cube.send_prompt(index)

    def do_hints_on(self, args):
        """
Turns on hints for the faces

This will auto turn-on every time the cube is solved
"""
        self.cube.turn_hints_on()

    def do_hints_off(self, args):
        """
Turns off hints for the faces. The lights will no longer light up

This will auto turn-on every time the cube is solved, or after HEYKUBE sleeps
"""
        self.cube.turn_hints_off()

    def do_get_orientation(self, arg):
        """
Tells you which HEYKUBE face is up
"""
        if self.check_connected():
            face_up, accel = self.cube.read_accel()
            print('{} face up'.format(face_up))

    def do_print_cube(self, args):
        """
Prints the current state of the cube
"""
        self.cube.print_cube()

    def complete_debug_level(self, text, line, begidx, endidx):

        completions = list()
        levels = ['info', 'warning', 'error']

        if not text:    
            completions = levels
        else:
            completions = [f for f in levels if f.startswith(text) ]

        return completions

    def do_debug_level(self, args):
        """
Sets the level of debug info to provide across all the components
usage:  debug_level [info | warning | error ]
"""
        modules = ['heykube', 'heykube_btle', 'heykube_cli']

        level = None
        if 'info' in args:
            level = logging.INFO
        elif 'warning' in args:
            level = logging.WARNING
        elif 'error' in args:
            level = logging.ERROR

        if level:
            for name in modules:
                logging.getLogger(name).setLevel(level)

    def do_track_cube(self, args):
        """
Tracks the cube until the user hits Ctrl-C
"""
        if self.check_connected():

            # get current sequence number
            start_state = self.cube.read_cube_state()
            print(self.cube.cube)
            prev_seq_num = start_state['seq_num']

            print('Tracking the HEYKUBE - hit Ctrl-C to clear move list, and Ctrl-C again to exit')
            self.cube.enable_notifications(['CubeState'])

            move_text = ''
            completed = False
            last_time = time.time() - 10
            
            while not completed:

                try:
                    while True:
                        num_moves, cube_status = self.cube.wait_for_cube_state(prev_seq_num=prev_seq_num, timeout=2)

                        if num_moves:
                            prev_seq_num = cube_status['seq_num']
                            move_text += ' {}'.format(cube_status['moves'])
                            print('Moves: {}'.format(move_text))
                            print(self.cube.cube)
    
                except KeyboardInterrupt:
                    if (time.time() - last_time) < 4:
                        print('\n\nDone tracking the cube')
                        completed = True
                    else:
                        last_time = time.time()
                        move_text = ''
                        print('\n\nClearing the move list\nHit Ctrl-C one more time to exit')
            self.cube.disable_notifications()

    def do_check_version(self, arg):
        """
Reports the Software version
"""
        if self.check_connected():
            version = self.cube.read_version()
            logger.info(version)
            print('Software version: {}'.format(version['version']))
            if not version['battery']:
                print('Battery voltage failed power-up checks')
            if not version['motion']:
                print('Accelerometer failed power-up checks')
            if version['custom_config']:
                print('Running a custom config')
            if not version['hints']:
                print('Hints are disabled')
            if version['full6']:
                print('Successfully detected the full6 Rotation self-check')
                print('   Moves: UUUU LLLL FFFF RRRR BBBB DDDD')
            if version['disconnect_reason'] != 0:
                if isinstance(version['disconnect_reason'], int):
                    print('BTLE disconnect code 0x{:02x}'.format(version['disconnect_reason']))
                else:
                    print('BTLE disconnect: {}'.format(version['disconnect_reason']))

    def do_reset(self, args):
        """ 
Full software reset of the cube -- use sparingly
"""

        # Reset the cube and disconnect
        self.cube.software_reset()
        self.connection.disconnect()

        # Go back to scan
        self.register_disconnect()

        time.sleep(2)
        self.run_scan()

    def do_write_instructions(self, args):
        """
Sends a custom instructions to the cube. This overrides the solver until the user follows the pattern
usage: write_instructions [U|L|F|R|B|D]['] ...

example:
write_instructions F U R U' R' F'
"""
        if self.check_connected():

            # Sets 
            instr = heykube.Moves(args)
            logger.info('Sending instructions: {}'.format(args))

            # Read instructions
            self.cube.write_instructions(instr)

    def do_get_instructions(self, args):
        """
Returns the current list of instructions in HEYKUBE
"""
        if self.check_connected():

            # Read instructions
            instr = self.cube.read_instructions()

            if len(instr) > 0:
                print('Instructions: {}'.format(instr))
            else:
                print('Instructions are empty')

    def do_enable_sounds(self, args):
        """
Turns on sounds for HEYKUBE
"""
        if self.check_connected():
            self.cube.enable_sounds()

    def do_disable_sounds(self, args):
        """
Turns off sounds from HEYKUBE until the next disconnect
"""
        if self.check_connected():
            self.cube.enable_sounds(False, False)

    def do_play_sound(self, args):
        """
Play one of the 8 sounds from HEYKUBE
usage: play_sound [0-7]
"""
        if self.check_connected():
            try:
                sound_index = int(args)
                if sound_index >= 0 and sound_index <= 7:
                    self.cube.play_sound(sound_index)
                else:
                    print('Error - pick a sound index between 0 and 7')
            except Exception as inst:
                print('Error - pick a sound index between 0 and 7')

    def do_get_moves(self, args):
        """
Returns the last moves applied to the cube. 
usage: get_moves    # get up to 42 previous moves
       get_moves 10 # get the last 10 moves
"""
        if self.check_connected():

            val = self.cube.read_moves()
            moves = val['moves']

            try:
                num_moves = int(args)
                if num_moves > len(moves):
                    num_moves = len(moves)
            except:
                num_moves = len(moves)

            if num_moves == 0:
                print('moves: ', moves)
            else:
                out_text = 'Last {} moves: '.format(num_moves)
                for loop1 in range(num_moves):
                    out_text += '{} '.format(moves[len(moves)-num_moves+loop1])
                print(out_text)

    def do_check_battery(self, args):
        """
Checks HEYKUBE battery status 
"""
        if self.check_connected():
            capacity, volt, charger = self.cube.read_battery()
            print('\nCapacity {}%, Battery voltage: {:0.2f}V, Charger status = {}'.format(capacity, volt, charger))

    def do_quit(self, args):
        """
Exits HEYKUBE Command line interface
"""
        if self.connection.is_connected():
            self.connection.disconnect()

        return True

    def help_quit(self):
        print("syntax: quit")

def main():
    print('Starting HEYKUBE Command line interface (CLI)')

    # Allocate the CLI
    cli = heykube_cli()

    # Run the CLI loop
    cli.cmdloop()

if __name__ == '__main__':
    main()
