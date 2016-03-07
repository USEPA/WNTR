# This is not an example script. This is a test the developers use to
# ensure all of the examples run.

import unittest
import sys
# HACK until resilience is a proper module
# __file__ fails if script is called in different ways on Windows
# __file__ fails if someone does os.chdir() before
# sys.argv[0] also fails because it doesn't not always contains the path
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..','..'))
from os import listdir
from os.path import isfile
from subprocess import call


class TestExamples(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_that_examples_run(self):
        example_files = [f for f in listdir(os.path.join(resilienceMainDir,'examples')) if isfile(os.path.join(resilienceMainDir,'examples',f)) and f.endswith('.py') and not f.startswith('test')]
        flag = 1
        for f in example_files:
            flag = call(['sys.executable', os.path.join(resilienceMainDir,'examples',f)])
            self.assertEqual(flag,0)
