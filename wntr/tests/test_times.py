import unittest
from os.path import abspath, dirname, join

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

# class TestNetworkTimeWarnings(unittest.TestCase):
#
#    @classmethod
#    def setUpClass(self):
#        import wntr
#        self.wntr = wntr
#
#    @classmethod
#    def tearDownClass(self):
#        pass
#
#    def test_pattern_start_time(self):
#        inp_file = join(test_datadir, 'net_test_8.inp')
#        wn = self.wntr.network.WaterNetworkModel()
#        parser = self.wntr.network.ParseWaterNetwork()
#
#        flag = False
#        with warnings.catch_warnings(record=True) as w:
#            warnings.simplefilter("always")
#            parser.read_inp_file(wn, inp_file)
#        for message in w:
#            if str(message.message) == 'Currently, only the EpanetSimulator supports a non-zero patern start time.':
#                flag = True
#        self.assertEqual(flag, True)
#
#    #def test_report_time_step(self):
#    #    inp_file = join(test_datadir, 'net_test_9.inp')
#    #    wn = self.wntr.network.WaterNetworkModel()
#    #    parser = self.wntr.network.ParseWaterNetwork()
#    #
#    #    flag = False
#    #    with warnings.catch_warnings(record=True) as w:
#    #        warnings.simplefilter("always")
#    #        parser.read_inp_file(wn, inp_file)
#    #    for message in w:
#    #        if str(message.message) == 'Currently, only a the EpanetSimulator supports a report timestep that is not equal to the hydraulic timestep.':
#    #            flag = True
#    #    self.assertEqual(flag, True)
#
#    def test_report_start_time(self):
#        inp_file = join(test_datadir, 'net_test_10.inp')
#        wn = self.wntr.network.WaterNetworkModel()
#        parser = self.wntr.network.ParseWaterNetwork()
#
#        flag = False
#        with warnings.catch_warnings(record=True) as w:
#            warnings.simplefilter("always")
#            parser.read_inp_file(wn, inp_file)
#        for message in w:
#            if str(message.message) == 'Currently, only the EpanetSimulator supports a non-zero report start time.':
#                flag = True
#        self.assertEqual(flag, True)
#
#    def test_start_clocktime(self):
#        inp_file = join(test_datadir, 'net_test_11.inp')
#        wn = self.wntr.network.WaterNetworkModel()
#        parser = self.wntr.network.ParseWaterNetwork()
#
#        flag = False
#        with warnings.catch_warnings(record=True) as w:
#            warnings.simplefilter("always")
#            parser.read_inp_file(wn, inp_file)
#        for message in w:
#            if str(message.message) == 'Currently, only the EpanetSimulator supports a start clocktime other than 12 am.':
#                flag = True
#        self.assertEqual(flag, True)


class TestNetworkTimeBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(test_datadir, "times.inp")
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        sim = self.wntr.sim.WNTRSimulator(wn)
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        pass

    def test_duration(self):
        results = self.results
        self.assertEqual(len(results.node["head"].index), 26)
        self.assertEqual(results.node["head"].index[25], 24 * 3600 + 3 * 3600 + 5 * 60)

    def test_report_timestep(self):
        results = self.results
        self.assertEqual(
            (results.node["head"].index[1] - results.node["head"].index[0]),
            1 * 3600 + 5 * 60,
        )

    def test_pattern_timestep(self):
        results = self.results
        for t in results.node["demand"].index:
            self.assertEqual(results.node["demand"].at[t, "junction1"], 1.0)
            total_seconds = t
            if (total_seconds / 3900.0) % 8 == 0.0 or (
                (total_seconds / 3900.0) - 1
            ) % 8 == 0.0:
                self.assertEqual(results.node["demand"].at[t, "junction2"], 0.5)
            elif (total_seconds / 3900.0) % 8 == 2.0 or (
                (total_seconds / 3900.0) - 1
            ) % 8 == 2.0:
                self.assertEqual(results.node["demand"].at[t, "junction2"], 1.0)
            elif (total_seconds / 3900.0) % 8 == 4.0 or (
                (total_seconds / 3900.0) - 1
            ) % 8 == 4.0:
                self.assertEqual(results.node["demand"].at[t, "junction2"], 1.5)
            elif (total_seconds / 3900.0) % 8 == 6.0 or (
                (total_seconds / 3900.0) - 1
            ) % 8 == 6.0:
                self.assertEqual(results.node["demand"].at[t, "junction2"], 1.0)


if __name__ == "__main__":
    unittest.main()
