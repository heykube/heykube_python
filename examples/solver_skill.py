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
import time

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
    
# Reinitialize the cube
while not cube.is_solved():
    print('Cube not solved - please solve the cube first')
    cube.disconnect()
    exit()

# ---------------------------------------------------------
# Setup helper language
# ---------------------------------------------------------
verbose = True
solver_text = dict()
if verbose:
    solver_text['scrambled'] = 'You are starting from a scrambled cube, starting working on the bottom cross'
    solver_text['bottom_cross'] = 'Now that you have the bottom cross,\nyou are working to get all the white face pieces in place'
    solver_text['bottom_layer'] = 'You are working to solve the middle layer,\nput the white face down and rotate the cube to look at the flash faces.\nThere are only two variations of patterns you need to learn to move pieces into the middle layer'
    solver_text['middle_layer'] = 'You are working on the yellow cross,\nyou may have to redo the pattern a few times'
    solver_text['top_layer_cross'] = 'The next phase is to move all the yellow pieces to the upper face.\nAgain you may have to repeat the pattern a few times.\nThere is only one pattern to learn for this step, but the it depends on which face'
    solver_text['top_layer_face'] = 'Now that all the yellow pieces are up, you are rotating the corners.\nPut the two correct corners in the back.\nIf the two correct pieces are diagonal, you may need to do the pattern twice'
    solver_text['top_layer_corner'] = 'You are very close! The last step is to rotate the edge pieces either clockwise or counterwise.\nIf four pieces are out of place, you may have to do it twice'
    solver_text['solved'] = 'The HEYKUBE is solved!'
else:
    solver_text['scrambled'] = 'Start with the bottom cross'
    solver_text['bottom_cross'] = 'Get all the white pieces in place'
    solver_text['bottom_layer'] = 'Solve the middle layer'
    solver_text['middle_layer'] = 'Get the yellow cross'
    solver_text['top_layer_cross'] = 'Move all the yellow pieces to the top'
    solver_text['top_layer_face'] = 'Rotate corners into place'
    solver_text['top_layer_corner'] = 'Rotate edge pieces'
    solver_text['solved'] = 'The HEYKUBE is solved!'

# ----------------------------------------------------
# Start the solver
# ----------------------------------------------------
try:
    
    # Config the cube
    print('Welcome to the solver tutorial. You are going to learn to solve the cube.')
    print('')
    print('Follow the lights on the cube to scramble it -- you have 60 seconds')
    
    # Sends 18 random moves
    scramble = heykube.Moves()
    scramble.randomize(18)

    # Send the instructions to the queue
    cube.write_instructions(scramble)

    # Turn on the notifications and wait for scramble
    cube.enable_notifications(['instruction_empty'])
    num_moves, cube_status = cube.wait_for_notify(timeout=60)
    
    if 'instruction_empty' in cube_status:
        print("Cube is now scrambled -- starting solving")
    else:
        print('You waited too long to scramble')
        cube.disconnect()
        exit()
    
    # ---------------------------------------------------------
    # Check if the cube is ready
    # ---------------------------------------------------------

    # Print the cube
    cube.print_cube()
    
    # clear any other notifications
    #cube.clear_notify()
    
    # Send monitoring the commands
    cube.enable_notifications(['solution', 'instruction_empty', 'instruction_max',  'move'])
    
    # Wait for notify
    num_moves, cube_status = cube.wait_for_notify(timeout=30)
    if 'move' in cube_status:
        print('Starting the timer -- GO')
        print(cube_status) 
        start_time = cube_status['timestamp']
        num_moves, cube_status = cube.wait_for_notify(timeout=30)
    else:
        print('Move not registered')
        print(cube_status) 
    
    # Should only take 30 sections
    for loop1 in range(30):
    
        # -----------------------------------------
        # Simulate user reading instruction queue
        # -----------------------------------------
        instr = cube.read_instructions()
        print('Found instructions: ', instr)
    
        # -----------------------------------------
        # Wait for moves
        # -----------------------------------------
        num_moves, cube_status = cube.wait_for_notify(timeout=30)

        # Check the solution
        if 'solution' in cube_status:
            new_solution = cube_status['solution']
    
            # Handle the solved case
            if 'solved' in new_solution[0]:
                final_move = cube_status['seq_num']
                end_time = cube_status['timestamp']
    
                solve_time = cube.subtract_time(end_time, start_time)
                print('')
                if solve_time >= 60.0:
                    minutes = int(solve_time // 60.0)
                    seconds = solve_time % 60.0
                    print('Hurray! You solved HEYKUBE in {} minutes {:0.2f} seconds'.format(minutes, seconds))
                else:
                    print('Hurray! You solved HEYKUBE in {:0.2f} seconds'.format(solve_time))
                break
            else:
                print('----------------------------------------------------------------------')
                print('Moved to {}'.format(new_solution[0]))
                print('')
                print(solver_text[new_solution[0]])
                print('')
        elif 'instruction_max' in cube_status:
                print('You seem to be ignoring the hints on the HEYKUBE. Follow the light rings directions to learn to solve the cube')
    
        # Print the cube
        cube.print_cube()
    
# Handling exceptions and breakout
except KeyboardInterrupt:
    print('Exiting after Cntrl-c')
except Exception as e:
    print('Trapping exception {}'.format(e))
# Disconnect and cleanup
finally:
    cube.disable_notifications()
    cube.disconnect()
