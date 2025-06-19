import unittest
import os
import shutil
from os.path import abspath, dirname, join
from wntr.network import WaterNetworkModel
from wntr.library import ModelLibrary, model_library

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

class TestModelLibrary(unittest.TestCase):
    def test_model_name_list(self):
        self.assertIn("Net3", model_library.model_name_list)
        self.assertIn("ky4", model_library.model_name_list)
    
    def test_get_model(self):
        model = model_library.get_model("ky4")
        self.assertIsInstance(model, WaterNetworkModel)
        
    def test_model_construction(self):
        # Test construction from name
        model = WaterNetworkModel("ky4")
        
    def test_add_directory(self):
        # Test adding a directory
        model_library.add_directory(test_datadir)
        self.assertIn("io", model_library.model_name_list)
        
        # Test getting the filepath after adding a directory
        filepath = model_library.get_filepath("io")
        self.assertEqual(filepath, join(test_datadir, "io.inp"))
        
        # Test construction from file path
        model = WaterNetworkModel("io")
        self.assertIsInstance(model, WaterNetworkModel)


if __name__ == "__main__":
    unittest.main()
