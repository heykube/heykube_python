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
from heykube import heykube_btle
from enum import Enum
from queue import Queue
import time
import random
import math
import logging
import json

# -------------------------------------------------
# -------------------------------------------------
# Setup Logging capability
# -------------------------------------------------
# -------------------------------------------------
logging.basicConfig()
logger = logging.getLogger('heykube')

# ---------------------------------------------------------
# ---------------------------------------------------------
# Defines the HEYUBE internal structure
# ---------------------------------------------------------
# ---------------------------------------------------------

# --------------------------------------------------------
# Match class - helps to compare cube state with patterns
# --------------------------------------------------------
class Match():
    """Defines the Match() class which enables HEYKUBE to match with
certain patterns, and provide a notification
    """

    def __init__(self, init_set=None):

        # helps iterator
        self.iter_index = 0

        # setup the don't care
        self.match_state = [Cube_Color.DontCare]*54
        self.clear()

        # initialize
        if init_set:
            if isinstance(init_set, Cube):
                for loop1 in range(54):
                    self.match_state[loop1] = Cube_Color(init_set.state[loop1] // 9)
            elif isinstance(init_set, str):
                if len(init_set) == 1:
                   self.add_face(init_set)     
                else:
                    self.add_cubie(init_set)

    # -------------------------------------------------------
    # Basic operators
    # -------------------------------------------------------
    def decode_state(self, data):
        
        ptr = 0
        bit_pos = 0

        # go through all the faces
        for loop1 in range(54):
            if (loop1 % 9) == 4:
                self.match_state[loop1] = Cube_Color(hoop1 // 9)    
            else:
                # update bits
                color_index = (data[ptr] >> bit_pos) & 0x7;

                # get overflow
                if bit_pos == 6:
                    color_index |= (data[ptr+1] & 0x1) << 2
                elif bit_pos == 7:
                    color_index |= (data[ptr+1] & 0x3) << 1

                matchState[loop1] = Cube_Color(color_index)

                bit_pos += 3;
                if bit_pos >= 8:
                    bit_pos -= 8
                    ptr += 1


    def encode_state(self):

        cstate = [0]*18
        ptr = 0
        bit_pos = 0
        for loop1 in range(54):

            # only process non-center pieces
            if (loop1 % 9) != 4:
                cstate[ptr] |= (self.match_state[loop1].value << bit_pos) & 0xff
    
                # overflow cases
                if bit_pos == 6:
                    cstate[ptr+1] |= self.match_state[loop1].value >> 2
                elif bit_pos == 7:
                    cstate[ptr+1] |= self.match_state[loop1].value >> 1
    
                # update state
                bit_pos += 3
                if bit_pos >= 8:
                    bit_pos -= 8
                    ptr += 1

        return cstate

    def __assign__(self, other):
        y = Match()
        for loop1 in range(54):
            y.match_state[loop1] = other.match_state[loop1]
        return y

    def __invert__(self):

        y = Match()
        for loop1 in range(54):
            if self.match_state[loop1] == Cube_Color.DontCare:
                y.match_state[loop1] = Cube_Color(loop1//9)
            else:
                y.match_state[loop1] = Cube_Color.DontCare
        # restore center
        for loop1 in range(6):
            y.match_state[loop1*9+4] = Cube_Color(loop1)

        return y

    def __add__(self, other):
        y = Match()
        # copy the state
        for loop1 in range(54):
            y.match_state[loop1] = self.match_state[loop1]

        for loop1 in range(54):
            if other.match_state[loop1].value < 6:
                y.match_state[loop1] = other.match_state[loop1]
        return y

    def __sub__(self, other):
        y = Match()
        # copy the state
        for loop1 in range(54):
            y.match_state[loop1] = self.match_state[loop1]

        for loop1 in range(54):
            if other.match_state[loop1].value < 6:
                y.match_state[loop1] = Cube_Color.DontCare

        # restore center
        for loop1 in range(6):
            y.match_state[loop1*9+4] = Cube_Color(loop1)

        return y

    def __iter__(self):
        self.iter_index = 0
        return self

    def __next__(self):
        if self.iter_index < 54:
            y = [Facelet(self.iter_index), self.match_state[self.iter_index]]
            self.iter_index += 1
            return y
        else:
            raise StopIteration

    def to_list(self):

        y = list()
        index = 0
        while index < 54:
            y.append(self.match_state[index].value)
            index += 1
            # skip centers
            if index % 9 == 4:
                index += 1

        return y

    # -------------------------------------------------------
    # Setup match operations
    # -------------------------------------------------------

    # clear up after substract/inversion
    def restore_center(self):
        for loop1 in range(6):
            self.match_state[loop1*9+4] = Cube_Color(loop1)

    def clear(self):
        """Clears the match object back to don't care on all Facelets"""
        for loop1 in range(54):
            self.match_state[loop1] = Cube_Color.DontCare
        self.restore_center()

    def add_cubie(self, facelet_name):
        facelets = Facelet(facelet_name).cubie()
        for facelet in facelets:
            self.match_state[int(facelet)] = facelet.color()

    def add_facelet(self, facelet_name):
        facelet = Facelet(facelet_name)
        self.match_state[int(facelet)] = facelet.color()

    def add_layer(self, face='U'):
        self.add_face(face)

    def add_two_layer(self,face='U'):
        self.add_layer(face)
        try:
            color_sets = { 'U' : [10, 16, 19, 25, 28, 34, 37, 43],
                           'L' : [ 3, 5, 21, 23, 48, 50, 39, 41],
                           'F' : [ 1, 7, 30, 32, 52, 46, 14, 12],
                           'R' : [ 3, 5, 21, 23, 48, 50, 39, 41],
                           'B' : [30, 32, 1, 7, 46, 52, 12, 14],
                           'D' : [19, 25, 28, 34, 37, 43, 10, 16]}
            for index in color_sets[face]:
                self.match_state[index] = Cube_Color(index//9)
        except:
            logger.error('Match.add_two_layer({}) is an illegal face specification'.format(face))

    def solved(self):
        """Sets the match to a fully solved cube"""
        for loop1 in range(6):
            for loop2 in range(9):
                self.match_state[9*loop1+loop2] = Cube_Color(loop1)

    def add_cross(self, face):
        """Sets the match for the cross on that face"""
        try:
            self.add_cross_color(face)
            color_sets = { 'U' : [12, 21, 30, 39],  
                           'L' : [ 1, 19, 46, 43],  
                           'F' : [ 5, 28, 48, 16],  
                           'R' : [25, 52, 37,  7],  
                           'B' : [ 3, 34, 50, 10],  
                           'D' : [23, 32, 41, 14]}  
            for index in color_sets[face]:
                self.match_state[index] = Cube_Color(index//9)
        except:
            logger.error('Match.add_cross({}) is an illegal face specification'.format(face))

    def add_cross_color(self, face_name):
        """Sets the match for a cross - but just colors on that face"""
        try:
            facelet = Facelet(face_name)
            face_index = facelet.color().value
            for loop1 in range(4):
                self.match_state[face_index*9+2*loop1+1] = Cube_Color(face_index)
        except:
            logger.error('Match.add_cross_color({}) is an illegal face specification'.format(face))

    def add_face(self, face):
        """Sets the match for the colors on that face"""
        self.add_face_color(face)
        try:
            color_sets = { 'U' : [ 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42],
                           'L' : [ 0,  1,  2, 18, 19, 20, 45, 46, 47, 42, 43, 44],
                           'F' : [ 2,  5,  8, 27, 28, 29, 51, 48, 45, 17, 16, 15],
                           'R' : [ 6,  7,  8, 24, 25, 26, 51, 52, 53, 36, 37, 38],
                           'B' : [33, 34, 35, 47, 50, 53,  0,  3,  6,  9, 10, 11],
                           'D' : [20, 23, 26, 29, 32, 35, 38, 41, 44, 11, 14, 17]}  
            for index in color_sets[face]:
                self.match_state[index] = Cube_Color(index//9)
        except:
            logger.error('Match.add_face({}) is an illegal face specification'.format(face))

    def add_face_color(self, face_name):
        try:
            facelet = Facelet(face_name)
            face_index = facelet.color().value
            for loop1 in range(9):
                self.match_state[face_index*9+loop1] = Cube_Color(face_index)
        except:
            logger.error('Match.add_face_color({}) is an illegal face specification'.format(face))

    # -----------------------------------------------------------
    # Print output
    # -----------------------------------------------------------
    def print_piece_square(self, color_index):
        if (color_index == Cube_Color.Red):
            text = "\033[48;5;124m\033[30m Re \033[0m"
        elif (color_index == Cube_Color.White):
            text = "\033[107m\033[30m Wh \033[0m"
        elif (color_index == Cube_Color.Orange):
            text = "\033[48;5;202m\033[30m Or \033[0m"
        elif (color_index == Cube_Color.Yellow): 
            text = "\033[48;5;11m\033[30m Ye \033[0m"
        elif (color_index == Cube_Color.Blue):
            text = "\033[48;5;27m\033[30m Bl \033[0m"
        elif (color_index == Cube_Color.Green):
            text = "\033[102m\033[30m Gr \033[0m"
        else:
            text = "\033[48;5;241m\033[30m    \033[0m"
        return text

    def __str__(self):
        cube_str = ''
        ptr = 0

        # print upper state
        cube_str += "\n"
        for loop1 in range(3):
            cube_str += "            "
            for loop2 in range(3):
                cube_str += self.print_piece_square(self.match_state[ptr+3*loop2])
            cube_str += "\n"
            ptr += 1
    
        # print core middle
        ptr = 9
        for loop1 in range(3):
            for loop2 in range(12):
                cube_str += self.print_piece_square(self.match_state[ptr+3*loop2])
            cube_str += "\n";
            ptr += 1
    
        # print down
        ptr = 45
        for loop1 in range(3):
            cube_str += "            "
            for loop2 in range(3):
                cube_str += self.print_piece_square(self.match_state[ptr+3*loop2])
            cube_str += "\n"
            ptr += 1
        cube_str += "\n"

        return cube_str

# -----------------------------------------------
# Defines Cube moves - builds up the translation
# to HEYKUBE index, and from the string notation
# ----------------------------------------------
class Moves():
    """Defines the moves for HEYKUBE and translates
betwen cubing notication U|L|F|R|B|D and the HEYKUBE index"""

    def __init__(self, move_str=''):
        self.move_list = list()
        self.move_index = 0

        # Define the direct face rotations and indices 
        self.FaceRotations = {
            "U"  : 0,  "L"  : 1,
            "F"  : 2,  "R"  : 3, 
            "B"  : 4,  "D"  : 5,
            "U'" : 8,  "L'" : 9,
            "F'" : 10, "R'" : 11, 
            "B'" : 12, "D'" : 13,
            # change orientation
            "x"  : 16, "y"  : 17, "z"  : 18,
            "x'" : 24, "y'" : 25, "z'" : 26,
        }
        self.InvFaceRotations = dict((self.FaceRotations[k], k) for k in self.FaceRotations)

        # setup dual face rotaions
        self.DoubleFaceRotations = {
            "u"  : ["D",  "y"],
            "l"  : ["R",  "x'"],
            "f"  : ["B",  "z"],
            "r"  : ["L",  "x"],
            "b"  : ["F",  "z'"],
            "d"  : ["U",  "y'"],
            "u'" : ["D'", "y'"],
            "l'" : ["R'", "x"],
            "f'" : ["B'", "z'"],
            "r'" : ["L'", "x'"],
            "b'" : ["F'", "z"],
            "d'" : ["U'", "y"]
        }

        # setup dual face rotaions
        self.CenterRotations = {
            "M"   : ["x'", "L'", "R"],
            "E"   : ["y'", "U",  "D'"],
            "S"   : ["z",  "F'", "B"],
            "M'"  : ["x",  "L",  "R'"],
            "E'"  : ["y",  "U'", "D"],
            "S'"  : ["z'", "F",  "B'"],
        }

        # Define absolution rotations
        self.AbsFaceRotations = {
            "Wh"  : 0, "Or"   : 1,
            "Gr"  : 2, "Re"   : 3, 
            "Bl"  : 4, "Ye"   : 5,
            "Wh'" : 8, "Or'"  : 9,
            "Gr'" : 10, "Re'" : 11, 
            "Bl'" : 12, "Ye'" : 13
        }

        # add moves
        self.add_moves(move_str)

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        self.move_index = 0
        return self

    def __len__(self):
        return len(self.move_list)

    def __add__(self, other):
        y = Moves()
        for val in self.move_list:
            y.move_list.append(val)    
        for val in other.move_list:
            y.move_list.append(val)    
        return y

    def clear(self):
        """Clears the list of moves"""
        self.move_list = list()

    def absolute(self):

        # set the orientation
        self.orientation = {"U" : Cube_Color.White, "F" : Cube_Color.Green}

        self.order = {"U" : "U", "L" : "L", "F" : "F", "R" : "R", "B" : "B", "D" : "D"}

        abs_moves = Moves()
        for loop1 in range(len(self.move_list)):
            move = self.move_list[len(self.move_list)-1-loop1]
            move_index = self.FaceRotations[move]

            # Flip the list
            if (move_index & 0x8):
                move_index &= 0x7
            else:
                move_index |= 0x8
            reverse_moves.add(self.InvFaceRotations[move_index])
        return reverse_moves



    def reverse(self):
        """Returns a new Moves() object which is reversed.
The reverse the moves, and convert clockwise to counter-clockwise moves (and vice versa)"""

        reverse_moves = Moves()
        for loop1 in range(len(self.move_list)):
            move = self.move_list[len(self.move_list)-1-loop1]
            move_index = self.FaceRotations[move]

            # Flip the list
            if (move_index & 0x8):
                move_index &= 0x7
            else:
                move_index |= 0x8
            reverse_moves.add(self.InvFaceRotations[move_index])
        return reverse_moves

    def add_moves(self, move_str):
        """Add more moves to the list"""

        # Deal with lists
        if isinstance(move_str, list):
            for val in move_str:
                if isinstance(val, int):
                    self.move_list.append(self.InvFaceRotations[val])
                else:
                    self.move_list.append(self.FaceRotations[val])

        # Deal with strings
        else:
            # pad to check for 2x notation
            move_str += '  '

            # Deal with groupings
            while True:
                group_start = move_str.find('(')
                if group_start == -1:
                    break

                group_end = move_str.find(')')

                rot_group = move_str[group_start+1:group_end]

                # Double the group
                if move_str[group_end+1] == '2':
                    rot_group += ' '  
                    rot_group += rot_group  
                    group_end += 1
                elif move_str[group_end+1] == '3':
                    rot_group += ' '  
                    rot_group += rot_group + rot_group
                    group_end += 1

                # Rebuild string
                move_str = move_str[0:group_start] + rot_group + move_str[group_end+1:]

            # pad so we can check for extra parameters
            str_index = 0
            while str_index < len(move_str):

                if move_str[str_index] == ' ':
                    str_index += 1

                # Handle regular moves
                elif move_str[str_index] in self.FaceRotations:

                    # Get move
                    next_val = move_str[str_index]
                    str_index += 1
                    
                    num_moves = 1
                    if move_str[str_index] == '2':
                        num_moves = 2
                        str_index += 1
                    elif move_str[str_index] == '3':
                        num_moves = 3
                        str_index += 1

                    if move_str[str_index] == "'":
                        next_val += "'"
                        str_index += 1

                    for loop1 in range(num_moves):
                        self.move_list.append(next_val)

                # Handle double moves
                elif move_str[str_index] in self.DoubleFaceRotations:

                    # Get move
                    next_val = move_str[str_index]
                    str_index += 1
                    
                    num_moves = 1
                    if move_str[str_index] == '2':
                        num_moves = 2
                        str_index += 1
                    elif move_str[str_index] == '3':
                        num_moves = 3
                        str_index += 1
                    if move_str[str_index] == "'":
                        next_val += "'"
                        str_index += 1

                    next_set = self.DoubleFaceRotations[next_val]
                    for loop1 in range(num_moves):
                        self.move_list.extend(next_set)

                # Handle double moves
                elif move_str[str_index] in self.CenterRotations:

                    # Get move
                    next_val = move_str[str_index]
                    str_index += 1
                    
                    num_moves = 1
                    if move_str[str_index] == '2':
                        num_moves = 2
                        str_index += 1
                    elif move_str[str_index] == '3':
                        num_moves = 3
                        str_index += 1
                    if move_str[str_index] == "'":
                        next_val += "'"
                        str_index += 1

                    next_set = self.CenterRotations[next_val]
                    for loop1 in range(num_moves):
                        self.move_list.extend(next_set)

                else:
                    print('Cannot processing {}'.format(move_str[str_index]))
                    str_index += 1

    def __next__(self):
        if self.move_index < len(self.move_list):
            y = Moves()
            y.add(self.move_list[self.move_index])
            self.move_index += 1
            return y
        else:
            raise StopIteration

    def add(self, x):
        self.move_list.append(x)

    def __int__(self):
        if len(self.move_list) == 1:
            y = int(self.FaceRotations[self.move_list[0]])            
        else:
            y = list()
            for val in self.move_list:
                y.append(int(self.FaceRotations[val]))
        return y

    def __str__(self):
        move_str = ''
        for loop1, val in enumerate(self.move_list):

            move_str += self.move_list[loop1]
            if loop1 < (len(self.move_list)-1):
                move_str += ' '
        return move_str

    def __getitem__(self, index):
        y = Moves()
        if index < len(self.move_list):
            y.add(self.move_list[index])
        return y

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):

        if len(other.move_list) != len(self.move_list):
            return False
        else:

            match = True
            for loop1 in range(len(self.move_list)):
                if self.move_list[loop1] != other.move_list[loop1]:
                    match = False
                    break
            return match


    def scramble(self, num_rot):
        self.randomize(num_rot)

    def pattern_enable(self):
        """Returns the pattern enable sequence"""
        self.clear()
        self.add_moves("L' L' D' D' D D L L")

    def hints_on_off(self):
        """Returns the hints on/off sequence"""
        self.clear()
        self.add_moves("R R D D D' D' R' R'")

    def randomize(self, num_rot):
        """Provides a random scramble of moves

TODO -- this needs to be a WCA-type scramble"""

        self.move_list = list()  
        inv_last_move = random.randint(0,5) | (random.randint(0,1) << 3)
        for loop1 in range(num_rot):

            # make sure it's not just the inverted move
            next_move = inv_last_move
            while next_move == inv_last_move:
                next_move = random.randint(0,5) | (random.randint(0,1) << 3)
            inv_last_move = next_move ^ 0x8

            # Add the list
            self.move_list.append(self.InvFaceRotations[next_move])
        logger.info('Randomized moves: {}'.format(self.move_list))

    def from_string(self, rot_str):
        pass

# Defines Cube Faces and Colors
class Cube_Color(Enum):
    White = 0
    Orange = 1
    Green = 2
    Red = 3
    Blue = 4
    Yellow = 5 
    DontCare = 6

# -------------------------------------------
# Define Cube Facelet locations
# Helps in search for faces, and encoding
# -------------------------------------------
class Facelet():

    def __init__(self, facelet_name=''):

        # define facelets
        self.facelets = {             
            # UP FACE
            'ULB' :  0, 'UB' :  3, 'URB' :  6,
            'UL'  :  1, 'U'  :  4, 'UR'  :  7,
            'ULF' :  2, 'UF' :  5, 'UFR' :  8,
            # left FACE
            'LUB' :  9, 'LU' : 12, 'LUF' : 15,
            'LB'  : 10, 'L'  : 13, 'LF'  : 16,
            'LBD' : 11, 'LD' : 14, 'LFD' : 17,
            # Front FACE
            'FUL' : 18, 'FU' : 21, 'FUR' : 24,
            'FL'  : 19, 'F'  : 22, 'FR'  : 25,
            'FLD' : 20, 'FD' : 23, 'FRD' : 26,
            # Right FACE
            'RUF' : 27, 'RU' : 30, 'RUB' : 33,
            'RF'  : 28, 'R'  : 31, 'RB'  : 34,
            'RFD' : 29, 'RD' : 32, 'RBD' : 35,
            # Back FACE
            'BUR' : 36, 'BU' : 39, 'BUL' : 42,
            'BR'  : 37, 'B'  : 40, 'BL'  : 43,
            'BRD' : 38, 'BD' : 41, 'BLD' : 44,
            # Down FACE
            'DLF' : 45, 'DF' : 48, 'DFR' : 51,
            'DL'  : 46, 'D'  : 49, 'DR'  : 52,
            'DLB' : 47, 'DB' : 50, 'DRB' : 53
        }
        # get reverse LUT
        self.inv_facelets = dict()
        for keys in self.facelets.keys():
            self.inv_facelets[self.facelets[keys]] = keys

        # zero the iterator
        self.iter_index = 0

        # assing the value
        if isinstance(facelet_name,int):
            self.index = facelet_name
        elif facelet_name == '':
            self.index = 4
        else:

            # reorder
            if len(facelet_name) == 3:
                if int(Facelet(facelet_name[1])) > int(Facelet(facelet_name[2])):
                    facelet_name = '{}{}{}'.format(facelet_name[0], facelet_name[2], facelet_name[1])
            # get index
            self.index = self.facelets[facelet_name]

    def color(self):
        return Cube_Color(self.index//9)


    def __eq__(self, x, y):
        if int(x) == int(y):
            return True
        else:
            return False

    def __le__(self, other):
        return not self.__gt__(other)

    def __gt__(self, other):
        if self.index > int(other):
            return True
        else:
            return False

    def cubie(self):

        # get name of facelet
        facelet_name = self.__str__()

        cubie_facelets = list()

        if len(facelet_name) == 1:
            cubie_facelets.append(Facelet(facelet_name))
        elif len(facelet_name) == 2:
            cubie_facelets.append(Facelet(facelet_name))
            cubie_facelets.append(Facelet('{}{}'.format(facelet_name[1],facelet_name[0])))
        elif len(facelet_name) == 3:
            cubie_facelets = list()
            for loop1 in range(3):

                # get all 3 orders
                name = '{}{}{}'.format(facelet_name[loop1],
                                       facelet_name[(loop1+1) %3], 
                                       facelet_name[(loop1+2) %3])
                # sort it
                if Facelet(name[1]) > Facelet(name[2]):
                    name = '{}{}{}'.format(name[0], name[2], name[1])
                cubie_facelets.append(Facelet(name))

        return cubie_facelets

    def __int__(self):
        return self.index

    def __str__(self):
        return self.inv_facelets[self.index]

    def __iter__(self):
        self.iter_index = 0
        return self

    def __next__(self):
        if self.iter_index < 54:
            y = self.inv_facelets[self.iter_index]
            self.iter_index += 1
            return y
        else:
            raise StopIteration

# ---------------------------------------------------
# Main class to hold the model of a 3x3 cube
# ---------------------------------------------------
class Cube():

    def __init__(self):

        # Initialize the state
        self.state = list()
        for loop1 in range(54):
            self.state.append(loop1)
    
        # Defines debug level
        self.debug = 2

        # set the orientation
        self.orientation = {"U" : Cube_Color.White, "F" : Cube_Color.Green}

        # set moves
        self.moves = Moves()
        self.seq_num = 0

        # Setup state
        self.EdgePairs = [
            # Up
            [Facelet("UF"), Facelet("FU")],
            [Facelet("UR"), Facelet("RU")],
            [Facelet("UB"), Facelet("BU")],
            [Facelet("UL"), Facelet("LU")],
            # Down
            [Facelet("DF"), Facelet("FD")],
            [Facelet("DR"), Facelet("RD")],
            [Facelet("DB"), Facelet("BD")],
            [Facelet("DL"), Facelet("LD")],
            # middle 
            [Facelet("FR"), Facelet("RF")],
            [Facelet("FL"), Facelet("LF")],
            [Facelet("BR"), Facelet("RB")],
            [Facelet("BL"), Facelet("LB")]
        ]

        # Corner sets
        self.CornerSets = [
            # Up
            [Facelet("UFR"), Facelet("FUR"), Facelet("RUF")],
            [Facelet("URB"), Facelet("RUB"), Facelet("BUR")],
            [Facelet("ULB"), Facelet("BUL"), Facelet("LUB")],
            [Facelet("ULF"), Facelet("LUF"), Facelet("FUL")],
            # Down 
            [Facelet("DFR"), Facelet("RFD"), Facelet("FRD")],
            [Facelet("DLF"), Facelet("FLD"), Facelet("LFD")],
            [Facelet("DLB"), Facelet("LBD"), Facelet("BLD")],
            [Facelet("DRB"), Facelet("BRD"), Facelet("RBD")]
       ]


        self.rotationTable = [
          # ULFRBD
          [  2,  5,  8,  1,  4,  7,  0,  3,  6, 18, 10, 11, 21, 13, 14, 24, 16, 17, 27, 19, 20, 30, 22, 23, 33, 25, 26, 36, 28, 29, 39, 31, 32, 42, 34, 35,  9, 37, 38, 12, 40, 41, 15, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53], 
          [ 44, 43, 42,  3,  4,  5,  6,  7,  8, 11, 14, 17, 10, 13, 16,  9, 12, 15,  0,  1,  2, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 47, 46, 45, 18, 19, 20, 48, 49, 50, 51, 52, 53],
          [  0,  1, 17,  3,  4, 16,  6,  7, 15,  9, 10, 11, 12, 13, 14, 45, 48, 51, 20, 23, 26, 19, 22, 25, 18, 21, 24,  2,  5,  8, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 29, 46, 47, 28, 49, 50, 27, 52, 53],
          [  0,  1,  2,  3,  4,  5, 24, 25, 26,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 51, 52, 53, 29, 32, 35, 28, 31, 34, 27, 30, 33,  8,  7,  6, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 38, 37, 36],
          [ 33,  1,  2, 34,  4,  5, 35,  7,  8,  6,  3,  0, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 53, 50, 47, 38, 41, 44, 37, 40, 43, 36, 39, 42, 45, 46,  9, 48, 49, 10, 51, 52, 11],
          [  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 38, 12, 13, 41, 15, 16, 44, 18, 19, 11, 21, 22, 14, 24, 25, 17, 27, 28, 20, 30, 31, 23, 33, 34, 26, 36, 37, 29, 39, 40, 32, 42, 43, 35, 47, 50, 53, 46, 49, 52, 45, 48, 51],
          # (ULFRBD)'
          [  6,  3,  0,  7,  4,  1,  8,  5,  2, 36, 10, 11, 39, 13, 14, 42, 16, 17,  9, 19, 20, 12, 22, 23, 15, 25, 26, 18, 28, 29, 21, 31, 32, 24, 34, 35, 27, 37, 38, 30, 40, 41, 33, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53],
          [ 18, 19, 20,  3,  4,  5,  6,  7,  8, 15, 12,  9, 16, 13, 10, 17, 14, 11, 45, 46, 47, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,  2,  1,  0, 44, 43, 42, 48, 49, 50, 51, 52, 53],
          [  0,  1, 27,  3,  4, 28,  6,  7, 29,  9, 10, 11, 12, 13, 14,  8,  5,  2, 24, 21, 18, 25, 22, 19, 26, 23, 20, 51, 48, 45, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 15, 46, 47, 16, 49, 50, 17, 52, 53],
          [  0,  1,  2,  3,  4,  5, 38, 37, 36,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,  6,  7,  8, 33, 30, 27, 34, 31, 28, 35, 32, 29, 53, 52, 51, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 24, 25, 26],
          [ 11,  1,  2, 10,  4,  5,  9,  7,  8, 47, 50, 53, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,  0,  3,  6, 42, 39, 36, 43, 40, 37, 44, 41, 38, 45, 46, 35, 48, 49, 34, 51, 52, 33],
          [  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 20, 12, 13, 23, 15, 16, 26, 18, 19, 29, 21, 22, 32, 24, 25, 35, 27, 28, 38, 30, 31, 41, 33, 34, 44, 36, 37, 11, 39, 40, 14, 42, 43, 17, 51, 48, 45, 52, 49, 46, 53, 50, 47],
          # xyz
          [ 18, 19, 20, 21, 22, 23, 24, 25, 26, 15, 12,  9, 16, 13, 10, 17, 14, 11, 45, 46, 47, 48, 49, 50, 51, 52, 53, 29, 32, 35, 28, 31, 34, 27, 30, 33,  8,  7,  6,  5,  4,  3,  2,  1,  0, 44, 43, 42, 41, 40, 39, 38, 37, 36], 
          [  2,  5,  8,  1,  4,  7,  0,  3,  6, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,  9, 10, 11, 12, 13, 14, 15, 16, 17, 51, 48, 45, 52, 49, 46, 53, 50, 47],
          [ 11, 14, 17, 10, 13, 16,  9, 12, 15, 47, 50, 53, 46, 49, 52, 45, 48, 51, 20, 23, 26, 19, 22, 25, 18, 21, 24,  2,  5,  8,  1,  4,  7,  0,  3,  6,  42, 39, 36, 43, 40, 37, 44, 41, 38, 29, 32, 35, 28, 31, 34, 27, 30, 33],
          # (xyz)'
          [ 44, 43, 42, 41, 40, 39, 38, 37, 36, 11, 14, 17, 10, 13, 16,  9, 12, 15,  0,  1,  2,  3,  4,  5,  6,  7,  8, 33, 30, 27, 34, 31, 28, 35, 32, 29, 53, 52, 51, 50, 49, 48, 47, 46, 45, 18, 19, 20, 21, 22, 23, 24, 25, 26],
          [  6,  3,  0,  7,  4,  1,  8,  5,  2, 36, 37, 38, 39, 40, 41, 42, 43, 44,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 47, 50, 53, 46, 49, 52, 45, 48, 51],
          [ 33, 30, 27, 34, 31, 28, 35, 32, 29,  6,  3,  0,  7,  4,  1,  8,  5,  2, 24, 21, 18, 25, 22, 19, 26, 23, 20, 51, 48, 45, 52, 49, 46, 53, 50, 47, 38, 41, 44, 37, 40, 43, 36, 39, 42, 15, 12,  9, 16, 13, 10, 17, 14, 11]
        ]

    def initialize(self):
        self.clear_moves()
        for loop1 in range(54):
            self.state[loop1] = loop1

    def apply_moves(self, moves):

        # go through the moves
        for move in moves:

            # create new state
            new_state = [0]*54

            # get table index
            move_index = int(move)     
            if (move_index >= 0) and (move_index <= 5):
                table_index = move_index
            elif (move_index >= 8) and (move_index <= 13):
                table_index = move_index - 2
            elif (move_index >= 16) and (move_index <= 18):
                table_index = move_index - 4
            elif (move_index >= 24) and (move_index <= 26):
                table_index = move_index - 9
            else:
                table_index = None
                logger.error('Illegal move specification {}'.format(move))

            # with a valid entry run the move
            if not table_index is None:
                rotSet = self.rotationTable[table_index]
                for loop1 in range(54):
                    new_state[loop1] = self.state[rotSet[loop1]]
                self.state = new_state

                # keep track
                #print('Adding {} move to the cube'.format(move))
                self.moves.add_moves([move_index])
                # updating seq number
                self.seq_num += 1
                self.seq_num &= 0xff

    def get_orientation(self):
        orientation = dict()

        orientation['U'] = self.get_location_color(Facelet("U"))
        orientation['F'] = self.get_location_color(Facelet("F"))
        logger.info('Orientation = {}'.format(orientation))

        return orientation


    def reset_orientation(self):
        logger.info('Resetting orientation')

        # moves the white face
        if self.get_location_color(Facelet("L")) == Cube_Color.White:
            self.apply_moves(Moves("z"))
        elif self.get_location_color(Facelet("F")) == Cube_Color.White:
            self.apply_moves(Moves("x"))
        elif self.get_location_color(Facelet("R")) == Cube_Color.White:
            self.apply_moves(Moves("z'"))
        elif self.get_location_color(Facelet("B")) == Cube_Color.White:
            self.apply_moves(Moves("x'"))
        elif self.get_location_color(Facelet("D")) == Cube_Color.White:
            self.apply_moves(Moves("x x"))
        #print(self.__str__())

        # moves the Green face
        if self.get_location_color(Facelet("L")) == Cube_Color.Green:
            self.apply_moves(Moves("y'"))
        elif self.get_location_color(Facelet("R")) == Cube_Color.Green:
            self.apply_moves(Moves("y"))
        elif self.get_location_color(Facelet("B")) == Cube_Color.Green:
            self.apply_moves(Moves("y y"))
        #print(self.__str__())

    def is_solved(self):
        solved = True
        for loop1 in range(54):
            if self.state[loop1] != loop1:
                solved = False
        return solved

    def test_match(self, match):
        match_test = True
        for loop1 in range(54):
            if match.match_state[loop1] != Cube_Color.DontCare:
                facelet_color = Cube_Color(self.state[loop1]//9)
                if facelet_color != match.match_state[loop1]:
                    match_test = False
        return match_test

    # Returns current cube state
    def get_state(self): 
        return self.encode_state()

    # decode a permuation
    def decodePerm(self, lex, n):
        a = list()
        for loop1 in range(n):
            a.append(0)

        i = n-2
        while i >= 0:
            a[i] = lex % (n - i)
            lex //= n-i
            for j in range(i+1, n):
                if a[j] >= a[i]:
                    a[j] += 1
            i -= 1
        return a


    def encodePerm(self, a):

        # Permtation enocder
        perm_popcount64 = [0,1,1,2,1,2,2,3, 1,2,2,3,2,3,3,4, 1,2,2,3,2,3,3,4, 2,3,3,4,3,4,4,5,
                           1,2,2,3,2,3,3,4, 2,3,3,4,3,4,4,5, 2,3,3,4,3,4,4,5, 3,4,4,5,4,5,5,6 ]

        n = len(a)
        bits = 0
        r = 0
        for i in range(n):
            bits |= 1 << a[i]
            low = ((1<<a[i])-1) & bits
            r = r * (n-i) + a[i] - perm_popcount64[low>>6] - perm_popcount64[low&63]
        if ((bits + 1) != (1 << n)):
            return -1
        return r

    # --------------------------------------------------------
    # Encoding format is derived from the spec
    # https://experiments.cubing.net/cubing.js/spec/binary/index.html
    # 
    # it appears to bit-reverse over original format
    # --------------------------------------------------------
    def encode_state(self):

        # setup 11 byte encoding
        cstate = [0]*11

        # -------------------------------------------------------
        # get the 12 edges pieces
        # -------------------------------------------------------
        edge_orient = 0;
        cubies = [-1]*12

        for loop1 in range(12):
            # get piece
            edgePiece = self.state[int(self.EdgePairs[loop1][0])]

            # find the piece number
            edge_orient <<= 1
            for loop2 in range(12):
                for loop3 in range(2):
                    if edgePiece == int(self.EdgePairs[loop2][loop3]):
                        cubies[loop1] = loop2
                        edge_orient += loop3
                if cubies[loop1] >= 0:
                    break

        # get the permutation
        encode = self.encodePerm(cubies) & 0x1fffffff
        for loop1 in range(4):
            cstate[loop1] = encode & 0xff
            encode >>= 8

        # encode the state variable
        cstate[3] |= (edge_orient & 0x7) << 5;
        edge_orient >>= 3
        cstate[4] = edge_orient & 0xff
        edge_orient >>= 8
        cstate[5] = edge_orient & 0x1

        # ------------------------------------------------------
        # Get the corner Pieces
        # ------------------------------------------------------
        corner_orient = 0;
        cubies = [-1]*8
        for loop1 in range(8):
            cornerPiece = self.state[int(self.CornerSets[loop1][0])]
	
            corner_orient *= 3
            for loop2 in range(8):
                for loop3 in range(3):
                    if cornerPiece == int(self.CornerSets[loop2][loop3]):
                        cubies[loop1] = loop2
                        corner_orient += loop3
                if cubies[loop1] >= 0:
                    break

        # get the permutation
        encode = self.encodePerm(cubies) & 0xffff
        cstate[5] |= (encode & 0x7f) << 1
        encode >>= 7
        cstate[6] = encode & 0xff
        encode >>= 8
        cstate[7] = encode & 0x1

        # encoder corner orientation
        cstate[7] |= (corner_orient & 0x7f) << 1
        corner_orient >>= 7
        cstate[8] = corner_orient & 0x3f

        # puzzle orientation 
        # always U, L = 0,0
        # Center locations are encoded
        center_orient = 0
        cstate[9] = 0x8 | ((center_orient & 0xf) << 4)
        cstate[10] = center_orient >> 4

        return cstate

    # gets list of perm/orientation from cstate
    def recover_cstate_data(self, cstate):

        valid_state = True

        # get edge perm
        r = cstate[0]
        r |= cstate[1] << 8
        r |= cstate[2] << 16
        r |= (cstate[3] &0x1f) << 24

        edge_orient = cstate[3] >> 5
        edge_orient |= cstate[4] << 3
        edge_orient |= (cstate[5] & 0x1) << 11;

        # decode permutation
        edge_perm = self.decodePerm(r, 12)

        # get corner perm
        r = cstate[5] >> 1
        r |= cstate[6] << 7
        r |= (cstate[7] & 0x1) << 15

        # decode permutation
        corner_perm = self.decodePerm(r, 8)

        # get corner orientation
        corner_orient = cstate[7] >> 1
        corner_orient |= (cstate[8] & 0x3f) << 7

        # get position of Faces - must be 0x0, 0x0
        pos = cstate[8] >> 6
        pos |= (cstate[9] & 0x7) << 2
        if pos != 0:
            valid_state = False

        # get order
        if (cstate[9] & 0x8):
            center_orient = cstate[9] >> 4
            center_orient |= cstate[10] << 4
        else:
            center_orient = 0

        return (valid_state, edge_perm, edge_orient, corner_perm, corner_orient, center_orient)

    # --------------------------------------------------------------
    # recover decoded state
    # --------------------------------------------------------------
    def decode_state(self, cstate):

        # set new list
        new_state = list()
        for loop1 in range(54):
            new_state.append(loop1)

        # Set the center stage
        for loop1 in range(6):
            centerPiece = loop1*9+4
            new_state[centerPiece] = centerPiece

        # get the permuatioitatio
        valid_state, edge_perm, edge_orient, corner_perm, corner_orient, center_orient = self.recover_cstate_data(cstate)
        # put edge pieces into location
        loop1 = 11
        while loop1 >= 0:
            orient_index = edge_orient & 0x1
            for loop2 in range(2):
                edgeLoc = int(self.EdgePairs[loop1][loop2])
                edgePiece = int(self.EdgePairs[edge_perm[loop1]][orient_index])
                new_state[edgeLoc] = edgePiece
                orient_index ^= 0x1
            # shift out orientation
            edge_orient >>= 1
            loop1 -= 1 

        # Get corner permutation
        loop1 = 7
        while loop1 >= 0:
            orient_index = corner_orient % 3
            for loop2 in range(3):
                cornerLoc   = int(self.CornerSets[loop1][loop2])
                cornerPiece = int(self.CornerSets[corner_perm[loop1]][orient_index])
                orient_index = (orient_index + 1) % 3

                new_state[cornerLoc] = cornerPiece

            # shift out
            corner_orient //= 3;
            loop1 -= 1

        # Check the final sum
        piece_sum = 0
        for loop1 in range(54):
            piece_sum += new_state[loop1]
        if piece_sum != 1431:
            valid_state = False

        return (valid_state, new_state, center_orient)

    def clear_moves(self):
        self.moves.clear()

    # Sets state from cstate
    def set_state(self, cstate):

        if len(cstate) < 20:
            print('Need a list of 20 integers')
            return False
        
        # Update cube states
        valid_cube, new_state, center_orient = self.decode_state(cstate)
        if valid_cube:
            self.state = new_state

        # Update moves
        new_seq_num = cstate[11]
        new_moves = (new_seq_num - self.seq_num) % 256

        move_list = list()
        for loop1 in range(9):
            next_move = cstate[loop1+12] & 0xf
            if next_move != 0xf:
                move_list.append(next_move)
            next_move = (cstate[loop1+12] >> 4) & 0xf
            if next_move != 0xf:
                move_list.append(next_move) 
        # shorten to new moves
        #print('new_seq_num = {}, prev = {}'.format(new_seq_num, self.seq_num))
        #print('Shorting: ', move_list)
        if (new_moves < len(move_list)):
            move_list = move_list[len(move_list)-new_moves:]
        #print('By {} moves: '.format(new_moves),  move_list)
        # Update tracking
        self.moves.add_moves(move_list)
        self.seq_num = new_seq_num
        self.timestamp = (cstate[21] + cstate[22] << 8) / 512.0
        
        return valid_cube


    # --------------------------------------------------------
    # Helper functions
    # --------------------------------------------------------
    def get_location_color(self, cube_index):
        color = Cube_Color(self.state[int(cube_index)] // 9)
        return color

    def get_piece_color(self, cube_index):
        color = Cube_Color(int(cube_index) // 9)
        return color

    def print_piece_square(self, val, label=True):
        color_index = self.get_piece_color(val)
        text = ''
        if (color_index == Cube_Color.Red):
            text = "\033[101m"
            text = "\033[48;5;124m"
        elif (color_index == Cube_Color.White):
            text = "\033[107m"
        elif (color_index == Cube_Color.Orange):
            text = "\033[48;5;202m"
        elif (color_index == Cube_Color.Yellow): 
            text = "\033[48;5;11m"
        elif (color_index == Cube_Color.Blue):
            text = "\033[48;5;27m"
        elif (color_index == Cube_Color.Green):
            text = "\033[102m"
        text += "\033[30m"
        if label:
            text += " {:2} ".format(val)
        else:
            text += "    ".format(val)
        text += "\033[0m"

        return text

    def __ne__(self,other):
        return not self.__eq__(other)

    def __eq__(self,other):
        for loop1 in range(54):
            if (other.state[loop1] != self.state[loop1]):
                return False
        return True

    def __repr__(self):

        # print state
        str_val = '{{ "state" : ['
        for loop1 in range(53):
            str_val += '{}, '.format(self.state[loop1])
        str_val += '{}]}}'.format(self.state[53])

        return str_val

    def __str__(self):
        cube_str = ''
        ptr = 0

        # print upper state
        cube_str += "\n"
        for loop1 in range(3):
            cube_str += "            "
            for loop2 in range(3):
                cube_str += self.print_piece_square(self.state[ptr+3*loop2])
            cube_str += "\n"
            ptr += 1
    
        # print core middle
        ptr = 9
        for loop1 in range(3):
            for loop2 in range(12):
                cube_str += self.print_piece_square(self.state[ptr+3*loop2])
            cube_str += "\n";
            ptr += 1
    
        # print down
        ptr = 45
        for loop1 in range(3):
            cube_str += "            "
            for loop2 in range(3):
                cube_str += self.print_piece_square(self.state[ptr+3*loop2])
            cube_str += "\n"
            ptr += 1
        cube_str += "\n"

        return cube_str

# -------------------------------------------------
# -------------------------------------------------
# Main HEYKUBE Object  
# -------------------------------------------------
# -------------------------------------------------
class heykube():
    """Defines the HEYKUBE class 
    
Includes ability to connect/disconnect from HEYKUBEs
Program lights and sounds
Send custom instructions
Query the cube state, register for moves and notifications
    """

    def __init__(self):
        self.cube = Cube()
    
        # Defines debug level
        self.debug = 0

        # Setup logging
        self.logger = logging.getLogger('heykube')

        # defines connection
        self.connectivity = heykube_btle()


        # setup time step
        self.time_step = 1.0/512

        # Initialize BTLE device
        self.notify_queue = self.connectivity.notify_queue
        self.device_name = None

        # Report the states
        self.notify_states = ['solution', 'move', 'match', 'double_tap', 'instruction_empty', 'instruction_max']
        self.solution_states = ['scrambled', 'bottom_cross', 'bottom_layer', 
                                'middle_layer', 'top_layer_cross', 
                                'top_layer_face', 'top_layer_corner', 'solved']
        # mark default last sequence
        self.last_status_seq_num = None

        # patterns
        self.pattern_names = ['checkerboard', 'sixspots', 'cubeincube', 'anaconda', 
                              'tetris', 'dontcrossline', 'greenmamba', 'spiralpattern', 
                              'python', 'kilt', 'cubeincubeincube', 'orderinchaos', 
                              'plusminus', 'displacedmotif', 'cuaround', 'verticalstripes'] 


    def connect(self, device):
        """Connects to a specified HEYKUBE device
device is a BLEDevice from bleak, and should be used from get_device"""
        # connect 
        success = self.connectivity.connect(device)

        # Clear notifications
        self.clear_notify()

        return success

    def disconnect(self):
        """Disconnects from a HEYKUBE device and clean-up connection"""
        return self.connectivity.disconnect()

    def get_device(self):
        """Scans input args and finds a HEYKUBE for connection
Defines the HEYKUBE connection options

optional arguments:
  -h, --help            show this help message and exit
  --verbose             increase output verbosity
  -n NAME, --name NAME  Directly defines name of a HEYKUBE for connection
  -a ADDRESS, --address ADDRESS
                        Directly defines an HEYKUBE MAC address for connection
  -s, --scan            Scans and reports all the available HEYKUBES
  -d, --debug           Turns on debug prints"""

        # Get the args
        args, _ = self.connectivity.parse_args()

        # Setup debug info
        if args.debug:
            print('Setting logger levels')
            logger.setLevel(logging.INFO)
            self.connectivity.logger.setLevel(logging.INFO)

        # get the device
        device = self.connectivity.get_device(args)

        return device

    def read_cube(self, field):
        return self.connectivity.read_cube(field)
    
    def write_cube(self, field, data,wait_for_response=True):
        success = self.connectivity.write_cube(field, data, wait_for_response)
        # TODO for now, make sure command is written before we return 
        time.sleep(0.2)
        return success

    # Enable notifications
    def enable_notifications(self, notify_list):
        """Registers for notifications from HEYKUBE"""

        if 'CubeState' in notify_list:
            self.connectivity.subscribe('CubeState')
        else:
            # arm the notifications
            status_flag = 0
            for loop1, val in enumerate(self.notify_states):
                if val in notify_list:
                    status_flag |= 1 << loop1
            self.write_cube('Status', [status_flag])
            self.connectivity.subscribe('Status')

    def disable_notifications(self):
        """Disables BTLE notifications"""
        self.connectivity.unsubscribe('CubeState')
        self.connectivity.unsubscribe('Status')

    def wait(self, timeout=10):
        """This method is used to wait for specified time
        """
        start_time = time.time()
        while True:
            current_time = time.time()
            if (current_time - start_time) >= timeout:
                break
            else:
                time.sleep(0.1)

    def wait_for_cube_state(self,prev_seq_num=None, timeout=10):
        """This method is used to wait for events from the HEYKUBE
        and includes a timeout mechanism if the event never happens
 
        :param timeout: Specifies the timeout duration in seconds
        :type timeout: float.
        :returns: dict -- Returns a dictionary with notifications events, None is status is empty

         'solution'          : 'scrambed:x' | 'bottom_cross:x' | 'bottom_layer:x' | 
                                'middle_layer:x' | 'top_layer_cross:x' | 
                                'top_layer_face:x' | 'top_layer_corner:x' |
                                'solved:0' - where x is [0-3],
          'last_move'         : 'o|O|w|W|r|R|y|Y|b|B|g|G',
          'timestamp'         : <running time in secs>,
          'match'             : True,
          'double_tap'        : True,
          'charger'           : True,
          'instruction_empty' : True,
          'instruction_max'   : True,
          'seq_num'           :  [0-255]
        
        """

        status_out = dict()
        num_moves = 0

        # Wait for timeout, keep heartbeart alive
        start_time = time.time()
        while True:

            current_time = time.time()
            if not self.notify_queue.empty():
                status_message = self.notify_queue.get()
                if status_message[0] == 'CubeState':
                    self.cube.set_state(status_message[1])
                    logger.info('{} notification'.format(status_message[0]))
                    #status_out['cube_state'] = True
                    status_out['seq_num'] = status_message[1][11]
                    status_out['moves'] = Moves()

                    # commpute number of moves
                    if prev_seq_num is None:
                        num_moves = 1
                    else:
                        num_moves = (status_out['seq_num'] - prev_seq_num) & 0xff

                    # build the list of new moves
                    index = 42 - num_moves  
                    move_list = []
                    for loop1 in range(num_moves):
                        if index & 0x1:
                            next_move = (status_message[1][index//2] >> 4) & 0xf
                        else:
                            next_move = status_message[1][index//2] & 0xf
                        move_list.append(next_move)
                        index += 1
                    
                    # append the list
                    status_out['moves'].add_moves(move_list)
                    break

            elif (current_time - start_time) >= timeout:
                #cube_state_end = self.read_cube_state()
                break
            else:
                time.sleep(0.1)

        # Parse status bytes
        return num_moves, status_out

    def wait_for_notify(self, prev_seq_num=None, timeout=10):
        """This method is used to wait for events from the HEYKUBE
and includes a timeout mechanism if the event never happens

:param timeout: Specifies the timeout duration in seconds
:type timeout: float.
:returns: dict -- Returns a dictionary with notifications events, None is status is empty

    'solution'          : 'scrambed:x' | 'bottom_cross:x' | 'bottom_layer:x' | 
                          'middle_layer:x' | 'top_layer_cross:x' | 
                          'top_layer_face:x' | 'top_layer_corner:x' |
                          'solved:0' - where x is [0-3],
    'last_move'         : 'U|L|F|R|B|D[']',
    'match'             : True,
    'instruction_empty' : True,
    'instruction_max'   : True,
    'seq_num'           : [0-255]
    'timestamp'         : <running time in seconds>
"""
        status_out = dict()

        # Wait for timeout, keep heartbeart alive
        start_time = time.time()
        while True:

            # Track time
            current_time = time.time()

            # Check the queue
            if not self.notify_queue.empty():
                status_message = self.notify_queue.get()
                if status_message[0] == 'Status':
                    status_bytes = status_message[1]
                    status_out = self.parse_status_info(status_bytes[1:6])
                    curr_seq_num = status_out['seq_num']
                    logger.info('Status notification - {}'.format(status_out))
                else:
                    logger.error('Unknown status notification - {}'.format(status_message[0]))
                    cube_state_end = self.read_cube_state()
                    curr_seq_num = cube_state_end['seq_num']
                    status_out['seq_num'] = cube_state_end['seq_num']
                    status_out['timestamp'] = cube_state_end['timestamp']
                break
            elif (current_time - start_time) >= timeout:
                logger.warning('Timeout in the Status notification')
                cube_state_end = self.read_cube_state()
                curr_seq_num = cube_state_end['seq_num']
                status_out['seq_num'] = cube_state_end['seq_num']
                status_out['timestamp'] = cube_state_end['timestamp']
                break
            else:
                time.sleep(0.1)

        # compute number of moves 
        if prev_seq_num:
            print('computing moves')
            num_moves = (curr_seq_num - prev_seq_num) & 0xff
        else:
            num_moves = 0

        # Parse status bytes
        return num_moves, status_out

    def get_notify(self):
        """Get immediate notification from the queue if it is there, otherwise returns None"""

        status_out = None
        if not self.notify_queue.empty():
            status_message = self.notify_queue.get()
            if status_message[0] == 'Status':
                status_bytes = status_message[1]
                status_out = self.parse_status_info(status_bytes[1:6])
            elif status_message[0] == 'CubeState':
                self.cube.set_state(status_message[1])
                status_out = True
            return [status_message[0], status_out]

        return None

    def clear_notify(self):
        """ Clear out old notify messages we do not need """
        while not self.notify_queue.empty():
            self.notify_queue.get()
    # ----------------------------------------------------------------------
    # Commands to control the cube
    # ----------------------------------------------------------------------
    def get_pattern_names(self):
        """Returns all the pattern names"""
        return self.pattern_names

    def get_pattern_name(self, index):
        """Returns a pattern name for a given index"""
        return self.pattern_names[index & 0xf]

    # Setup test mode
    def read_moves(self, prev_seq_num=None):
        """Reads up to the last 42 moves from HEYKUBE"""

        # Read the moves
        y = self.read_cube('Moves')
        val = dict()
        val['seq_num'] = y[0]
        moves_list = list()
        for loop1 in range(20): 
            
            next_move = y[loop1+1] & 0xf 
            if (next_move != 0xf):
                moves_list.append(next_move)
            next_move = (y[loop1+1] >> 4) & 0xf 
            if (next_move != 0xf):
                moves_list.append(next_move)

        # drop last moves
        if prev_seq_num:
            num_moves = (val['seq_num'] - prev_seq_num) & 0xff
            moves_list = moves_list[-num_moves:]

        # Form full list
        val['moves'] = Moves()
        val['moves'].add_moves(moves_list)
        val['timestamp'] = (y[21] + (y[22] << 8)) * self.time_step

        return val

    # Setup test mode
    def read_version(self):
        """Reads the current SW version"""
        y = self.read_cube('Version')
        val = dict()

        out_text = '0x'
        for x in y:
            out_text += '{:02x}'.format(x)
        logger.info('HEYKUBE version: {}'.format(out_text))

        # form the version number
        val['version'] = 'v{}.{}'.format(y[1],y[0])
        logger.info('HEYKUBE firmware version {}'.format(val['version']))

        # check the accelerometer
        if (y[2] & 0x2):
            val['battery'] = True
            logger.info('    Battery voltage in range')
        else:
            val['battery'] = False

        # check the accelerometer
        if (y[2] & 0x4):
            val['motion'] = True
            logger.info('    Motion enabled')
        else:
            val['motion'] = False

        # Report the config
        if (y[2] & 0x8):
            val['full6'] = True
            logger.info('    FULL6 Moves')
        else:
            val['full6'] = False

        # Report the config
        if (y[2] & 0x10):
            val['custom_config'] = True
            logger.info('    Using custom config')
        else:
            val['custom_config'] = False

        # check the hints on/off
        if (y[2] & 0x20):
            val['hints'] = False
            logger.info('    Hints off')
        else:
            val['hints'] = True

        # Report BTLE disconnect
        if y[3] in self.connectivity.disconnect_reasons:
            val['disconnect_reason'] = self.connectivity.disconnect_reasons[y[3]]
        else:
            val['disconnect_reason'] = y[3]

        return val

    def enable_pattern(self, pattern):
        """If HEYKUBE is solved, enables instructiosn for the specified pattern"""

        # Simulate patterns
        num_patterns = len(self.pattern_names)

        # Get the pattern index
        pattern_index = None
        if isinstance(pattern, int):
            if (pattern < 0) or (pattern >= num_patterns):
                self.logger.error('Error, pattern index must be [0,{}]'.format(num_patterns-1))
            else:
                pattern_index = pattern
        else:
            for loop1, val in enumerate(self.pattern_names):
                if pattern == val:
                    pattern_index = loop1
                    break
        # Send the pattern index
        if not (pattern_index is None):
            y = [0x08, pattern_index]
            self.write_cube('Action', y)

    # Read the config back
    def read_config(self):
        y = self.read_cube('Config')
        if self.debug:
            text = 'write_config:'
            for val in y:
                text += ' 0x{:02x}'.format(val)    
            logger.info(text)
        return y

    def enable_match(self):
        """Enables the match to fire again since it disable after each match"""
        self.write_cube('MatchState', [1])
    def disable_match(self):
        """Disables the match from firing"""
        self.write_cube('MatchState', [0])

    def set_match(self, match, enable=True):
        """This method allows the user to set the match from the class Match object"""
        data = list()

        # Enable the match
        if enable:
            data.append(1)
        else:
            data.append(0)

        match_list = match.to_list()
        next_byte = 0
        bit_pos = 0
        for loop1, val in enumerate(match_list):

            next_byte |= (val & 0x7) << bit_pos
            bit_pos += 3

            if (bit_pos >= 8):
                data.append(next_byte & 0xff)
                next_byte >>= 8
                bit_pos -= 8
        self.write_cube('MatchState', data)

    def clear_instructions(self):
        """Clears the instructions queue, and returns to the internal solver"""
        self.write_cube('Instructions', [0x0])

    def append_instructions(self, instr_moves):
        """Appends more instructions to the instructions queue"""
        self.write_instructions(instr_moves, append=True)

    def write_instructions(self, instr_moves, append=False):
        """This method allows the user to send a custom list of instructions
        to the HEYKUBE device. The faces on the LEDs will light up in
        sequence the users defines
 
        :param Class Moves(): Holds the list of moves
        """
        data = list()
        if len(instr_moves) > 52:
            logger.error('Too many instructions')
            return

        # convert into absolute rotations - TODO
        # Need to add teh X/Y/Y rotations
        # rot_cmd = self.cube.get_absolute_rotations(rot_cmd)
        if len(instr_moves) == 0:
            data.append(0)
            data.append(0xff)
            logger.info('write_instructions: send empty packet to clear it')
        else:
            logger.info('write_instructions: {}'.format(instr_moves))
            data.append(len(instr_moves))
            if append:
                data[0] |= 0x80
            for loop1, move in enumerate(instr_moves):
                val = int(move) & 0xf
    
                # Todo TODO - translate rotations"
                if (loop1 % 2) == 0:
                    data.append(val)
                else:
                    data[-1] |= val  << 4
            if len(instr_moves) & 0x1:
                data[-1] |= 0xf0

        self.write_cube('Instructions', data)

    def read_instructions(self):
        """This method connects to the HEYKUBE and reads-out the current
        list of instructions that are currently in queue
 
        :returns: str -- Returns the list of rotations
        """
        y = self.read_cube('Instructions')

        # process instructions
        num_inst = y[0]
        instr_list = list()
        skip = False
        # Read out list of instructions
        index = 1
        for loop1 in range(num_inst):
            # get value
            if (loop1 & 0x1):
                val = (y[index] >> 4) & 0xff
                index += 1
            else:
                val = y[index] & 0xf
            # append to list
            if skip:
                skip = False
            elif (val == 0x7) or (val == 0x6):
                skip = True
            else:
                instr_list.append(val)
        instr = Moves()
        instr.add_moves(instr_list)

        logger.info('instructions: {}'.format(instr))
        return instr

    def initialize(self):
        """This method resets the internal state of the HEYKUBE back to the solved state
        """

        # initialize internal cube state
        cstate = [0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0] 

        # Send to the cube
        self.write_cube('CubeState', cstate)

        # Check back and clear previous moves
        self.read_cube_state()
        self.cube.clear_moves()

        if self.debug:
            print(self.cube)

    def is_solved(self):
        """This method checks if the HEYKUBE is in the solved state

        :returns:  bool -- Returns True is the cube is solved
        """
        self.read_cube_state()
        return self.cube.is_solved()

    def write_cube_state(self, state):
        """Overrides the internal cube state --expert only"""
        self.write_cube('CubeState', state)

    def get_seq_num(self):
        """Reads the current sequence number from the cube"""
        y = self.read_cube('CubeState')
        return int(y[11])

    def get_timestamp(self):
        """Reads the current timestamp from the cube"""
        y = self.read_cube('CubeState')
        timestamp = (y[21] + (y[22] << 8)) * self.time_step
        return timestamp

    def read_cube_state(self):
        y = self.read_cube('CubeState')
        self.cube.set_state(y)

        # get data from the cube
        val = dict()
        val['seq_num'] = int(y[11])
        moves_list = list()
        for loop1 in range(9): 
            
            next_move = y[loop1+12] & 0xf 
            if (next_move != 0xf):
                moves_list.append(next_move)
            next_move = (y[loop1+12] >> 4) & 0xf 
            if (next_move != 0xf):
                moves_list.append(next_move)
        # Form full list
        val['moves'] = Moves()
        val['moves'].add_moves(moves_list)
        val['timestamp'] = (y[21] + (y[22] << 8)) * self.time_step

        return val

    def read_status(self):
        """This method reads up to the last 3 status events registered in the HEYKUBE

        :returns: list -- Returns a list of the up to last 3 status events, None is status is empty
            status_dict :
             'solution'          : 'scrambed:x' | 'bottom_cross:x' | 'bottom_layer:x' | 
                                    'middle_layer:x' | 'top_layer_cross:x' | 
                                    'top_layer_face:x' | 'top_layer_corner:x' |
                                    'solved:0' - where x is [0-3],
              'last_move'         : 'o|O|w|W|r|R|y|Y|b|B|g|G',
              'timestamp'         : <running time in secs>,
              'match'             : True,
              'instruction_empty' : True,
              'instruction_max'   : True,
              'seq_num'           :  [0-255]}
        """

        # Read the characteristics
        data = self.read_cube('Status')

        # build the output
        status_out_list = list()

        # Check the last three sequence numbers
        for loop1 in range(4):

            # Grab sequence
            list_slice = data[loop1*5+1:loop1*5+6]
            status_out = self.parse_status_info(list_slice)
            
            if status_out:
                status_out_list.append(status_out)

        return status_out_list


    def read_last_status(self):
        status_out = self.read_status()
        if status_out is None:
            return status_out
        elif isinstance(status_out,list):
            return status_out[0]
        else:
            return status_out

    def read_accel(self):
        """This method returns the full orientation of the cube in space using 
        the on-board 3D-accelerometer
 
        :returns: which face is up, along with X,Y and Z acceleration vector
        """

        # Read the accelerometer data
        y = self.read_cube('Accel')

        accel_scale = 2.0/128.0
        accel_data = list()
        max_index = 0
        for loop1 in range(3):
            val = int(y[loop1])
            if val >= 128:
                val -= 256
            val *= accel_scale
            accel_data.append(val)

            # track max absolute value
            if abs(val) > abs(accel_data[max_index]):
                max_index = loop1


        # get the orientation
        face_up_set = [['White', 'Yellow'], ['Orange', 'Red'], ['Blue', 'Green']]

        max_val = accel_data[max_index]
        if max_val >= 0:
            face_up = face_up_set[max_index][1]
        else:
            face_up = face_up_set[max_index][0]
        
        return face_up, accel_data

    def calc_battery_capacity(self, batt_voltage):

        # battery capacity curves
        self.battery_capacity = { 'volt'    : [3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2],
                                 'capacity' : [0.0, 0.01, 0.03, 0.04, 0.05, 0.1, 0.18, 0.35, 0.65, 0.8, 0.9, 0.95, 1.0]}
        # convert voltage to battery life
        capacity = 0
        if batt_voltage < self.battery_capacity['volt'][0]:
            capacity = self.battery_capacity['capacity'][0]
        elif batt_voltage >= self.battery_capacity['volt'][-1]:
            capacity = self.battery_capacity['capacity'][-1]
        else:
            for loop1 in range(len(self.battery_capacity['volt'])-1):
                v0 = self.battery_capacity['volt'][loop1]
                v1 = self.battery_capacity['volt'][loop1+1]
                c0 = self.battery_capacity['capacity'][loop1]
                c1 = self.battery_capacity['capacity'][loop1+1]
            
                # compute fit
                if batt_voltage >= v0 and batt_voltage < v1:
                    capacity = (c1-c0)/(v1-v0)*(batt_voltage - v0) + c0
                    break
        return int(capacity*100)

    def read_battery(self):
        """Reads the battery status and charging state"""
        y = self.read_cube('Battery')
        if y[1] & 0x10:
            chrg_status = 1
        else:
            chrg_status = 0
    
        # voltage is u3.9 format
        batt_voltage  =  float(y[0] + ((y[1] & 0xf) << 8))
        batt_voltage /= 2.0**9

        # compute capacity 
        capacity = self.calc_battery_capacity(batt_voltage)

        return (capacity, batt_voltage, chrg_status)

    def software_reset(self):
        """This method issues a software reset through BTLE
        """
        actions = [0x04, 0x00, 0x34, 0x12, 0x45]
        self.write_cube('Action', actions, wait_for_response=False)

    # Sends a hint for the faces
    def send_hint(self, index):
        """This method plays a hint on the faces
        """
        actions = [0x0b,index]
        self.write_cube('Action', actions)

    # Play sounds
    def play_sound(self, select=0):
        """This method plays a sound on the HEYKUBE device
 
        :param select: Selects the sound index between 0-7
        :type name: int.
        """
        actions = [0x06, select & 0x7]
        self.write_cube('Action', actions)

    def light_led(self, led_index):
        """This method will manual light one of the LEDs on the cube
 
        :param face: Picks one of 6 faces to light up
        :type face: int.
        :param index: Picks 1 of 6 indexes
        """
        actions = [0x0d,led_index]
        self.write_cube('Action', actions)

    def turn_off_led(self):
        """This method turns off all the LEDs on the HEYKUBE
        """
        self.light_led(36)

    def flash_all_lights(self):
        """This method flashes all the LEDs on the HEYKUBE
        """
        actions = [0x7, 0x6]
        self.write_cube('Action', actions)

    def send_prompt(self, index):
        """This method flashes the LEDs on the HEYKUBE, typically used when the user 
        solves the cube
        """
        actions = [0x7, index % 6]
        self.write_cube('Action', actions)

    # --------------------------------------------------------------
    # Configure the cube
    # --------------------------------------------------------------

    def add_time(self, b, a):
        c = (b + a) % 128.0
        return c

    def subtract_time(self, b, a):
        c = (b - a) % 128.0
        return c

    def parse_status_info(self, status_bytes):

        # Get the raw dictionary   
        status_out = dict()

        # Check first notifaction
        if status_bytes[0] == 0:
            return None

        for loop1, field in enumerate(self.notify_states):
            if (status_bytes[0] & (1 << loop1)):
                status_out[field] = True

        # check solution level and change to levels
        if 'solution' in status_out.keys():
            num_correct = status_bytes[1] & 0x3
            solution_index = (status_bytes[1] >> 2) & 0x7
            #solution = '{}:{}'.format(self.solution_states[solution_index], num_correct)
            status_out['solution'] = [self.solution_states[solution_index], num_correct]

        # reports the sequence number
        status_out['seq_num'] = status_bytes[2]

        # Report timestamp
        timestamp = (status_bytes[3] + (status_bytes[4] << 8)) / 512.0
        status_out['timestamp'] = timestamp

        return status_out
        
    def turn_hints_off(self):
        """Turns hints off on HEYKUBE - they will return once solved
        """
        self.write_cube('Action', [0x0a,0x0])

    def turn_hints_on(self):
        """Turns HEYKUBE hints back on"""
        self.write_cube('Action', [0x09,0x0])

    def enable_sounds(self, major_sound=True, minor_sound=True):
        """Reenables HEYKUBE sounds if they were previous disables"""

        y = self.read_config()
        # Switch to instruction mode 
        new_config = y[0] & 0xe7 
        if major_sound:
            new_config |= 0x8
        if minor_sound:
            new_config |= 0x10
        self.write_config([new_config])

    def disable_sounds(self):
        """This method temporarily disables the sounds from the cube during the duration
        of the BTLE connection session
        """
        self.enable_sounds(False, False)

    def print_cube(self):
        """This method reads the current state of HEYKUBE and prints to the screen
        """
        self.read_cube_state()
        print(self.cube)

# ----------------------------------------------------
# Adds the HEYKUBE admin class
# ----------------------------------------------------
class heykube_admin(heykube):

    def __init__(self, connection: heykube_btle):
        heykube.__init__(self, connection)

    # -------------------------------------------
    # Override FLASH config 
    # -------------------------------------------
    def clear_flash_config(self):

        # Setup programming key
        config_key = [0x02, 0xa4, 0x1f, 0x7d, 0xcb,]
        config_key.extend([0]*11)

        # write the config
        self.write_cube('Action', config_key)

    def program_flash_config(self, config):

        # Setup programming key
        config_key = [0x02, 0xa4, 0x1f, 0x7d, 0xcb,]
        # encode the config
        config_key.extend(self.encode_config(config))
        # set the Magic number
        config_key.extend([0xad])

        # write the config
        self.write_cube('Action', config_key)

    def enable_bootloader(self):
        bootloader_key = [0x01, 0x32, 0x07, 0xca, 0xc4]
        self.write_cube('Action', bootloader_key, wait_for_response=False)

