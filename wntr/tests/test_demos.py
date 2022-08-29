import os
import sys
import unittest
import pytest
from os import listdir
from os.path import abspath, dirname, isfile, join
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

kernel_name = 'python%d' % sys.version_info[0]
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
    
    @pytest.mark.time_consuming
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
            
            with open(f) as file:
                nb = nbformat.read(file, as_version=4) 
                
            nb.metadata.get('kernelspec', {})['name'] = kernel_name            
            proc = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
            proc.allow_errors = True
            proc.preprocess(nb)
            
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
        if len(failed_examples) > 0:
            print("failed examples: {0}".format(failed_examples))
        self.assertEqual(flag, 0)

if __name__ == "__main__":
    unittest.main()
