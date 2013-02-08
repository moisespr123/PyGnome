#!/usr/bin/env python

"""
basic_types.py

The python version of the various type definitions used

Imports all the symbols from cy_basic_types.pyx

Adds some for Python-only use

"""

import numpy as np

from cy_gnome.cy_basic_types import * # pull everything from the cython code


mover_type = np.float64
world_point_type = np.float64
windage_type = np.float64

datetime_value_2d = np.dtype([('time', np.datetime64), 
                           ('value', mover_type,(2,))], align=True)

#----------------------------------------------------------------
# Mirror C++ structures, following are used by cython code to access C++ methods/classes
seconds = np.uint32 # model time is going to be given in seconds
world_point = np.dtype([('long', world_point_type),
                        ('lat', world_point_type),
                        ('z', world_point_type)],
                       align=True)
velocity_rec       = np.dtype([('u', np.double), ('v', np.double),], align=True)
time_value_pair    = np.dtype([('time', seconds), ('value', velocity_rec),], align=True)
ebb_flood_data    = np.dtype([('time', seconds), ('scale', np.float64),('type',np.int16)], align=True)

# This 2D world point is just used by shio and Cats at present
w_point_2d = np.dtype([('long', world_point_type),
                       ('lat', world_point_type)])                           

# In the C++ TypeDefs.h, the enum type for LEStatus is defined as a short
# this is also consistent with the definition in type_defs.pxd .. define it here to keep things consistent
status_code_type = np.int16

id_type = np.uint16
