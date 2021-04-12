import unittest
from os.path import abspath, dirname, join
import numpy as np
import pandas as pd
import wntr
from pandas.testing import assert_frame_equal, assert_series_equal

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")
net3dir = join(testdir, "..", "..", "examples", "networks")


class TestPopulationMetrics(unittest.TestCase):
    def test_population_net3(self):
        inp_file = join(net3dir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        pop = wntr.metrics.population(wn)
        expected = 79000
        error = abs((pop.sum() - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

    def test_population_net6(self):
        inp_file = join(net3dir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        pop = wntr.metrics.population(wn)
        expected = 152000
        error = abs((pop.sum() - expected) / expected)
        self.assertLess(error, 0.01)  # 1% error

    def test_population_impacted(self):  # tests query and population impacted

        pop = pd.Series([100, 200, 300, 400, 500], index=["J1", "J2", "J3", "J4", "J5"])

        # arg1 as a Series, arg2 as a scalar
        wsa = pd.Series([0.6, 0.7, 0.8, 0.9, 1], index=["J1", "J2", "J3", "J4", "J5"])
        pop_impacted = wntr.metrics.population_impacted(pop, wsa, np.less, 0.8)
        expected = pd.Series([100, 200, 0, 0, 0], index=["J1", "J2", "J3", "J4", "J5"])
        assert_series_equal(pop_impacted, expected, check_dtype=False)

        # arg1 as a Series, arg2 as a Series
        wsa = pd.Series([0.6, 0.7, 0.8, 0.9, 1], index=["J1", "J2", "J3", "J4", "J5"])
        wsa_threshold = pd.Series([1, 0, 1, 0, 1], index=["J1", "J2", "J3", "J4", "J5"])
        pop_impacted = wntr.metrics.population_impacted(
            pop, wsa, np.less_equal, wsa_threshold
        )
        expected = pd.Series(
            [100, 0, 300, 0, 500], index=["J1", "J2", "J3", "J4", "J5"]
        )
        assert_series_equal(pop_impacted, expected, check_dtype=False)

        # arg1 as a DataFrame, arg2 as a scalar
        wsa = pd.Series([0.6, 0.7, 0.8, 0.9, 1], index=["J1", "J2", "J3", "J4", "J5"])
        wsa = wsa.to_frame().transpose()
        wsa.loc[1, :] = [0, 1, 0, 1, 0]
        wsa.loc[2, :] = [1, 0, 1, 0, 1]
        pop_impacted = wntr.metrics.population_impacted(pop, wsa, np.less, 0.8)
        expected = pd.DataFrame(
            [[100, 200, 0, 0, 0], [100, 0, 300, 0, 500], [0, 200, 0, 400, 0]],
            columns=["J1", "J2", "J3", "J4", "J5"],
            index=[0, 1, 2],
        )
        assert_frame_equal(pop_impacted, expected, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
