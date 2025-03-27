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
        # Create a temporary directory for testing
        cls.tear_down_paths = list()
        cls.tear_down_paths.append(join(testdir, "temp_test_networks"))
        os.makedirs(cls.temp_test_dir, exist_ok=True)

        # Copy in two networks
        for file_name in ["io.inp", "Anytown.inp"]:
            src = join(test_datadir, file_name)
            dst = join(cls.temp_test_dir, file_name)
            if os.path.exists(src):
                shutil.copy(src, dst)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_test_dir):
            shutil.rmtree(cls.temp_test_dir)

    def test_model_name_list(self):
        library = ModelLibrary(self.temp_test_dir)
        self.assertIn("io", library.model_name_list)
        self.assertIn("Anytown", library.model_name_list)

    def test_get_model(self):
        library = ModelLibrary(self.temp_test_dir)
        model = library.get_model("io")
        self.assertIsInstance(model, WaterNetworkModel)

    def test_add_model(self):
        library = ModelLibrary(self.temp_test_dir)
        wn_model = WaterNetworkModel(join(self.temp_test_dir, "io.inp"))
        library.add_model("NewNet", wn_model)
        self.assertIn("NewNet", library.model_name_list)
        self.assertTrue(os.path.exists(join(self.temp_test_dir, "NewNet.inp")))

    def test_remove_model(self):
        library = ModelLibrary(self.temp_test_dir)
        library.add_model("TempNet", WaterNetworkModel(join(self.temp_test_dir, "io.inp")))
        library.remove_model("TempNet")
        self.assertNotIn("TempNet", library.model_name_list)
        self.assertFalse(os.path.exists(join(self.temp_test_dir, "TempNet.inp")))

    def test_copy_model(self):
        library = ModelLibrary(self.temp_test_dir)
        library.copy_model("io", "ioCopy")
        self.assertIn("ioCopy", library.model_name_list)
        self.assertTrue(os.path.exists(join(self.temp_test_dir, "ioCopy.inp")))

    def test_default_directory(self):
        library = ModelLibrary()
        self.assertGreater(len(library.model_name_list), 0, "Default ModelLibrary should not be empty.")
        
        # Test loading a model from the default library using WaterNetworkModel constructor
        wn1 = WaterNetworkModel("Net3")
        self.assertIsInstance(wn1, WaterNetworkModel)
        
        wn2 = WaterNetworkModel(join(ex_datadir, "Net3.inp"))
        assert wn1._compare(wn2)

if __name__ == "__main__":
    unittest.main()