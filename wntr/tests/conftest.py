import os
import shutil
import tempfile
from os.path import abspath, dirname, join

import matplotlib
matplotlib.use("Agg")

TEST_DIR = dirname(abspath(__file__))
NETWORKS_FOR_TESTING_DIR = join(TEST_DIR, "networks_for_testing")
DATA_FOR_TESTING_DIR = join(TEST_DIR, "data_for_testing")
EXAMPLES_NETWORKS_DIR = join(TEST_DIR, "..", "..", "examples", "networks")
EXAMPLES_DIR = join(TEST_DIR, "..", "..", "examples")

# Set WNTR_KEEP_TEST_ARTIFACTS=1 to write test output (plots, .inp/.bin/.rpt
# files) to tests/test-artifacts/<name> instead of a self-cleaning temp dir,
# for manual inspection after a test run.
KEEP_TEST_ARTIFACTS = os.environ.get("WNTR_KEEP_TEST_ARTIFACTS", "") not in ("", "0", "false", "False")
TEST_ARTIFACTS_DIR = join(TEST_DIR, "test-artifacts")


def make_artifact_dir(name):
    if KEEP_TEST_ARTIFACTS:
        path = join(TEST_ARTIFACTS_DIR, name)
        os.makedirs(path, exist_ok=True)
        return path
    return tempfile.mkdtemp(prefix=f"wntr_{name}_")


def cleanup_artifact_dir(path):
    if not KEEP_TEST_ARTIFACTS:
        shutil.rmtree(path, ignore_errors=True)
