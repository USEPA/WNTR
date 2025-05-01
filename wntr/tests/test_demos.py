import os
import sys
import unittest
import pytest
from os import listdir
from os.path import abspath, dirname, isfile, join
import nbformat
import pandas as pd
from pandas.testing import assert_frame_equal
from nbconvert.preprocessors import ExecutePreprocessor

kernel_name = 'python%d' % sys.version_info[0]
testdir = dirname(abspath(str(__file__)))
examplesdir = join(testdir, '..', '..', 'examples')

class TestDemos(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass
    
    def data_test(self, filename):

        # Check if simulation results match expected results
        expected_results = join(testdir, 'data_for_testing', filename)
        expected_results = pd.read_csv(expected_results, index_col = 0)
        expected_results.sort_index(axis=0, inplace=True)
        expected_results.sort_index(axis=1, inplace=True)
        
        simulation_results = filename
        simulation_results = pd.read_csv(simulation_results, index_col = 0)
        simulation_results.sort_index(axis=0, inplace=True)
        simulation_results.sort_index(axis=1, inplace=True)
        
        assert_frame_equal(expected_results, simulation_results)
        
    @pytest.mark.time_consuming
    def test_that_demos_run(self):
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
            else:
                if nb_name == 'pipe_segments_tutorial':
                    self.data_test('segment_break_junctions_impacted.csv')
                    self.data_test('segment_break_people_impacted.csv')
                elif nb_name == 'pipe_break_tutorial':
                    self.data_test('pipe_break_junctions_impacted.csv')
                    self.data_test('pipe_break_people_impacted.csv')
                elif nb_name == 'fire_flow_tutorial':
                    self.data_test('fire_flow_junctions_impacted.csv')
                    self.data_test('fire_flow_people_impacted.csv')
                elif nb_name == 'earthquake_tutorial':
                    self.data_test('earthquake_people_impacted.csv')
                    self.data_test('earthquake_people_impacted_wrepair.csv')
                    
        os.chdir(cwd)
        if len(failed_examples) > 0:
            print("failed demos: {0}".format(failed_examples))
        self.assertEqual(flag, 0)

if __name__ == "__main__":
    unittest.main()
