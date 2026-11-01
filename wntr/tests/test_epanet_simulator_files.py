import glob
import os
import shutil
import tempfile
import unittest
from os.path import join

import wntr

from wntr.sim.epanet import default_file_prefix

from _test_paths import (
    EXAMPLES_NETWORKS_DIR as ex_datadir,
)


class Test_Default_File_Prefix(unittest.TestCase):
    def test_prefix_is_unique(self):
        prefix1 = default_file_prefix()
        prefix2 = default_file_prefix()
        self.assertNotEqual(prefix1, prefix2)
        for prefix in (prefix1, prefix2):
            os.rmdir(os.path.dirname(prefix))

    def test_prefix_is_in_temp_directory(self):
        parent = os.path.dirname(default_file_prefix())
        self.assertEqual(os.path.dirname(parent), tempfile.gettempdir())
        self.assertTrue(os.path.basename(parent).startswith('wntr_'))
        os.rmdir(parent)


class Test_EpanetSimulator_Files(unittest.TestCase):
    def test_default_run_sim_leaves_no_files_in_cwd(self):
        # a shared "temp" prefix made simulations in the same working
        # directory collide; the default must not write into the cwd
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp(prefix='wntr_test_')
        try:
            os.chdir(tmpdir)
            for _ in range(2):
                wn = wntr.network.WaterNetworkModel(join(ex_datadir, "Net1.inp"))
                wn.options.time.duration = 24 * 3600
                results = wntr.sim.EpanetSimulator(wn).run_sim()
                self.assertEqual(len(results.node['pressure'].index), 25)
            self.assertEqual(os.listdir(tmpdir), [])
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_default_run_sim_cleans_up_temp_files(self):
        # unique default prefixes must not pile up in the temp directory
        pattern = join(tempfile.gettempdir(), 'wntr_*')
        before = len(glob.glob(pattern))
        wn = wntr.network.WaterNetworkModel(join(ex_datadir, "Net1.inp"))
        wn.options.time.duration = 24 * 3600
        results = wntr.sim.EpanetSimulator(wn).run_sim()
        self.assertEqual(len(results.node['pressure'].index), 25)
        self.assertEqual(len(glob.glob(pattern)), before)

    def test_default_prefix_saves_and_reuses_hydraulics_file(self):
        # save_hyd/use_hyd without file_prefix or hydfile still use temp.hyd
        # in the working directory, so the saved hydraulics can be reused
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp(prefix='wntr_test_')
        try:
            os.chdir(tmpdir)
            wn = wntr.network.WaterNetworkModel(join(ex_datadir, "Net1.inp"))
            wn.options.time.duration = 24 * 3600
            sim = wntr.sim.EpanetSimulator(wn)
            sim.run_sim(save_hyd=True)
            self.assertEqual(os.listdir(tmpdir), ['temp.hyd'])
            results = sim.run_sim(use_hyd=True)
            self.assertEqual(len(results.node['pressure'].index), 25)
            self.assertEqual(os.listdir(tmpdir), ['temp.hyd'])
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_explicit_file_prefix_still_writes_files(self):
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp(prefix='wntr_test_')
        try:
            os.chdir(tmpdir)
            wn = wntr.network.WaterNetworkModel(join(ex_datadir, "Net1.inp"))
            wn.options.time.duration = 24 * 3600
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim(file_prefix=join(tmpdir, "test_net1"),
                                  save_hyd=True)
            self.assertEqual(len(results.node['pressure'].index), 25)
            for ext in ('.inp', '.rpt', '.bin', '.hyd'):
                self.assertTrue(
                    os.path.isfile(join(tmpdir, "test_net1" + ext)))
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
