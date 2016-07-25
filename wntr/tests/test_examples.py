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
        examples_dir = os.path.join(resilienceMainDir,'examples')
        cwd = os.getcwd()
        os.chdir(examples_dir)
        example_files = [f for f in listdir(examples_dir) if isfile(os.path.join(examples_dir,f)) and f.endswith('.py') and not f.startswith('test')]
        flag = 0
        for f in example_files:
            tmp_flag = call([sys.executable, os.path.join(resilienceMainDir,'examples',f)])
            if tmp_flag == 1:
                flag = 1
        os.chdir(cwd)
        self.assertEqual(flag,0)
