import atexit
import os
import shutil
import tempfile
from os.path import abspath, dirname, join

# Coerce mpl backend to non-interactive
import matplotlib
matplotlib.use("Agg")


# Manage working directory for testing
# WNTR_KEEP_TEST_ARTIFACTS="": no artifacts are saved
# WNTR_KEEP_TEST_ARTIFACTS="some/path": test artifacts are saved to this path
_keep_dir = os.environ.get("WNTR_KEEP_TEST_ARTIFACTS", "")
if _keep_dir:
    _test_cwd = abspath(_keep_dir)
    os.makedirs(_test_cwd, exist_ok=True)
else:
    _test_cwd = tempfile.mkdtemp(prefix="wntr_test_cwd_")
    atexit.register(shutil.rmtree, _test_cwd, ignore_errors=True)

_original_cwd = os.getcwd()
os.chdir(_test_cwd)
atexit.register(os.chdir, _original_cwd)

# Common dirs for testing
TEST_DIR = dirname(abspath(__file__))
NETWORKS_FOR_TESTING_DIR = join(TEST_DIR, "networks_for_testing")
DATA_FOR_TESTING_DIR = join(TEST_DIR, "data_for_testing")
EXAMPLES_NETWORKS_DIR = join(TEST_DIR, "..", "..", "examples", "networks")
EXAMPLES_DIR = join(TEST_DIR, "..", "..", "examples")
