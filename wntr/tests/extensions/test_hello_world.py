import unittest
import pytest

import wntr.extensions.hello_world as hello_world

@pytest.mark.extensions
class TestHelloWorld(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        pass
    
    @classmethod
    def tearDownClass(self):
        pass

    def test_hello_world(self):
        output = hello_world.example_module.example_function()
        assert output == "Hello World!"
        
if __name__ == "__main__":
    unittest.main()
