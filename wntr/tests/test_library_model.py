import unittest
import os
import shutil
from os.path import abspath, dirname, join
from wntr.network import WaterNetworkModel
from wntr.library import ModelLibrary

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

class TestModelLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        self.library = ModelLibrary()

    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_model_name_list(self):
        self.assertIn("Net3", self.library.model_name_list)
        self.assertIn("ky4", self.library.model_name_list)
    
    def test_get_model(self):
        model = self.library.get_model("ky4")
        self.assertIsInstance(model, WaterNetworkModel)
        
    def test_add_directory(self):
        # Test adding a directory
        self.library.add_directory(test_datadir)
        self.assertIn("io", self.library.model_name_list)
        
        # Test getting the filepath after adding a directory
        filepath = self.library.get_filepath("io")
        self.assertEqual(filepath, join(test_datadir, "io.inp"))

if __name__ == "__main__":
    unittest.main()
