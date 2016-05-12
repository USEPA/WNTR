"""
Python extensions for the EPANET Programmers Toolkit DLLs

Copyright 2011 Sandia Corporation Under the terms of Contract 
DE-AC04-94AL85000 there is a non-exclusive license for use of this 
work by or on behalf of the U.S. Government. Export of this program
may require a license from the United States Government.

This software is licensed under the BSD license. 

The PyEPANET module provides a wrapper around the EPANET programmer's 
tookit. The EN_XXX constants are defined in pyepanet.toolkit, but are 
imported by default as members of pyepanet. The ENepanet class is defined
in pyepanet.epanet2 and instantiating an object of this class loads the 
library and then provides pythonic functions equivalent to the EPANET 
tookit ENmethodname functions.
"""

from toolkit import *
from future import *
from epanet2 import ENepanet, EpanetException, ENgetwarning
import os, sys
from pkg_resources import Requirement, resource_filename

if os.name in ['nt','dos']:
    libepanet = resource_filename(__name__,'data/Windows/epanet2.dll')
elif sys.platform in ['darwin']:
    libepanet = resource_filename(__name__,'data/Darwin/libepanet.dylib')
else:
    libepanet = resource_filename(__name__,'data/Linux/libepanet2.so')
