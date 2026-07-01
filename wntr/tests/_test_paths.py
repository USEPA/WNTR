from os.path import abspath, dirname, join

TEST_DIR = dirname(abspath(__file__))
NETWORKS_FOR_TESTING_DIR = join(TEST_DIR, "networks_for_testing")
DATA_FOR_TESTING_DIR = join(TEST_DIR, "data_for_testing")
EXAMPLES_NETWORKS_DIR = join(TEST_DIR, "..", "..", "examples", "networks")
EXAMPLES_DIR = join(TEST_DIR, "..", "..", "examples")
