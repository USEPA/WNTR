import os
import sys
import unittest
import pytest
from os import listdir
from os.path import abspath, dirname, isfile, join
import nbformat
import pandas as pd
import geopandas as gpd
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
        
        self.nb_files = {
            ##TODO add file comparison tests for the basics and landslide tutorial
            #'basics_tutorial': ['Net3_analysis_pipes.geojson'],
            'earthquake_tutorial': ['earthquake_people_impacted.csv',
                                    'earthquake_people_impacted_wrepair.csv'],
            'fire_flow_tutorial': ['fire_flow_junctions_impacted.csv',
                                   'fire_flow_people_impacted.csv'],
            'getting_started_tutorial': ['pressure.csv'],
            #'landslide_tutorial': ['ky10_landslide_analysis_junctions.geojson'],
            'model_development_tutorial': ['wn1.inp', 
                                           'wn2.inp'],
            'multispecies_tutorial': ['chlorine_residual_1.3.csv'],
            'pipe_break_tutorial': ['pipe_break_junctions_impacted.csv',
                                    'pipe_break_people_impacted.csv'],
            'pipe_segments_tutorial': ['segment_break_junctions_impacted.csv',
                                       'segment_break_people_impacted.csv'],
            'salt_water_intrusion_tutorial': ['salt_water_baseline_quality.csv',
                                              'salt_water_response_quality.csv']
            }

    @classmethod
    def tearDownClass(self):
        pass

    def results_test(self, file1):
        # Check if jupyter notebook results (in file1) match expected results (in file2)
        file_extension = file1.split('.')[-1]
        assert file_extension in ['csv', 'geojson', 'inp'], file1
        
        file2 = join(testdir, 'data_for_testing', file1)

        if file_extension in ['csv', 'geojson']:
            if file_extension == 'csv':
                results1 = pd.read_csv(file1, index_col=0)
                results2 = pd.read_csv(file2, index_col=0)
            if file_extension == 'geojson':
                results1 = gpd.read_file(file1, index_col=0)
                results2 = gpd.read_file(file2, index_col=0)
            
            for axis in [0,1]:
                results1.sort_index(axis=axis, inplace=True)
                results2.sort_index(axis=axis, inplace=True)

        elif file_extension == 'inp':
            wn1 = self.wntr.network.WaterNetworkModel(file1)
            wn2 = self.wntr.network.WaterNetworkModel(file2)
            
            results1 = pd.DataFrame(wn1.describe(level=2))
            results2 = pd.DataFrame(wn2.describe(level=2))
        
        try:
            assert_frame_equal(results1, results2, rtol=1e-2, atol=1e-4)
            return True
        except:
            return False
        

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
            print(f)
            nb_name, file_extension = os.path.splitext(os.path.basename(f))
            
            with open(f) as file:
                nb = nbformat.read(file, as_version=4) 
                
            nb.metadata.get('kernelspec', {})['name'] = kernel_name            
            proc = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
            proc.allow_errors = True
            proc.preprocess(nb)
            
            # Test to make sure the demo runs
            runtime_errors = []
            for cell in nb.cells:
                if 'outputs' in cell:
                    for output in cell['outputs']:
                        if output.output_type == 'error':
                            runtime_errors.append(output)
            print('  runtime errors', len(runtime_errors))
            if len(runtime_errors) > 0:
                failed_examples.append(f)
                flag = 1
                continue
            
            # Test to make sure results are the same (based on a comparison of
            # results saved to file)
            file_errors = 0
            if nb_name in self.nb_files.keys():
                for file in self.nb_files[nb_name]:
                    if not self.results_test(file):
                        file_errors = file_errors + 1
                print('  file comparison errors', file_errors)
                if file_errors > 0:
                    failed_examples.append(f)
                    flag = 1
                    
        os.chdir(cwd)
        if len(failed_examples) > 0:
            print("failed demos: {0}".format(failed_examples))
        self.assertEqual(flag, 0)

if __name__ == "__main__":
    unittest.main()
