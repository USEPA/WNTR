# This is a test to ensure all of the examples run.
from __future__ import print_function
import unittest
import sys
import os
from os import listdir
from os.path import isfile, abspath, dirname, join
from subprocess import call

testdir = dirname(abspath(str(__file__)))
packdir = join(testdir,'..','..')

class TestExamples(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_that_examples_run(self):
        examples_dir = join(packdir,'examples')
        cwd = os.getcwd()
        os.chdir(examples_dir)
        example_files = [f for f in listdir(examples_dir) if isfile(join(examples_dir,f)) and f.endswith('.py') and not f.startswith('test')]
        flag = 0
        for f in example_files:
            tmp_flag = call([sys.executable, join(packdir,'examples',f)])
            print(f, tmp_flag)
            if tmp_flag == 1:
                flag = 1
        os.chdir(cwd)
        self.assertEqual(flag,0)

if __name__ == '__main__':
    unittest.main()
