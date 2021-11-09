# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 13:21:45 2021

@author: LCHUKETT
"""
import os
import unittest
from os import listdir
from os.path import abspath, dirname, isfile, join
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

testdir = dirname(abspath(str(__file__)))
examplesdir = join(testdir, '..', '..', 'examples', 'demos')

class TestExamples(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_that_examples_run(self):
        cwd = os.getcwd()
        os.chdir(examplesdir)
        example_files = [
            f
            for f in listdir(examplesdir)
            if isfile(join(examplesdir, f))
            and f.endswith(".ipynb")
            and not f.startswith("test")
        ]
        
        flag = 0
        failed_examples = []
        for f in example_files:           
            nb_name, file_extension = os.path.splitext(os.path.basename(f))
            # absolute_path = os.path.abspath(f) 
            
            with open(f) as file:
                nb = nbformat.read(file, as_version=4) 
                        
            proc = ExecutePreprocessor(timeout=600, kernel_name='python3')
            proc.allow_errors = True
            proc.preprocess(nb) #, {'metadata': {'path': '/'}})
            
            errors = []
            for cell in nb.cells:
                if 'outputs' in cell:
                    for output in cell['outputs']:
                        if output.output_type == 'error':
                            errors.append(output)
            print(f, len(errors))
            if errors:
                failed_examples.append(f)
                flag = 1   
                
        os.chdir(cwd)
        # print(errors)
        if len(failed_examples) > 0:
            print("failed examples: {0}".format(failed_examples))
        self.assertEqual(flag, 0)

if __name__ == "__main__":
    unittest.main()