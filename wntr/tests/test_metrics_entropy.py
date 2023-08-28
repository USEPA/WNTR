import unittest
from os.path import abspath, dirname, join

import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir, "networks_for_testing")


class TestEntropyMetric(unittest.TestCase):
    def test_layout1(self):
        inp_file = join(datadir, "Awumah_layout1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        attr = {
            "1": 940.7,
            "2": 550.0,
            "3": 659.3,
            "4": 290.7,
            "5": 400.0,
            "6": 59.3,
            "7": 450.0,
            "8": 200.0,
            "9": 300.0,
            "10": 250.0,
            "11": 100.0,
            "12": 150.0,
        }

        G_flowrate = wn.to_graph(link_weight=attr, modify_direction=True)

        [S, S_ave] = wntr.metrics.entropy(G_flowrate)

        # The values in the paper are different, perhaps due to significant figure
        # rounding during the calculation
        expected_Saverage = 0.0805  # 0.088
        error = abs((S.mean() - expected_Saverage) / expected_Saverage)
        self.assertLess(error, 0.05)  # 5% error

        expected_Smax = 0.5108  # 0.5130
        error = abs((S.max() - expected_Smax) / expected_Smax)

        expected_S_ave = 2.289  # 2.280
        error = abs((S_ave - expected_S_ave) / expected_S_ave)
        self.assertLess(error, 0.05)  # 5% error

    def test_layout8(self):
        inp_file = join(datadir, "Awumah_layout8.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        attr = {
            "1": 678.8,
            "2": 403.3,
            "3": 921.2,
            "4": 175.5,
            "5": 253.3,
            "6": 227.1,
            "7": 126.3,
            "8": 544.1,
            "9": 126.3,
            "10": 279.6,
            "11": 200.0,
            "12": 144.1,
            "13": 126.3,
            "14": 79.6,
            "15": 44.1,
            "16": 20.4,
        }

        G_flowrate = wn.to_graph(link_weight=attr, modify_direction=True)

        [S, S_ave] = wntr.metrics.entropy(G_flowrate)

        # The values in the paper are different, perhaps due to significant figure
        # rounding during the calculation
        expected_Saverage = 0.4391  # 0.3860
        error = abs((S.mean() - expected_Saverage) / expected_Saverage)
        self.assertLess(error, 0.05)  # 5% error

        expected_Smax = 1.1346  # 0.5130
        error = abs((S.max() - expected_Smax) / expected_Smax)
        self.assertLess(error, 0.05)  # 5% error

        expected_S_ave = 2.544  # 2.670
        error = abs((S_ave - expected_S_ave) / expected_S_ave)
        self.assertLess(error, 0.05)  # 5% error


if __name__ == "__main__":
    unittest.main()
