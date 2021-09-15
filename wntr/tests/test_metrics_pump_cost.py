import unittest
from os.path import abspath, dirname, join

import pandas as pd

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestPumpNet3(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import wntr

        self.wntr = wntr

        inp_file = join(ex_datadir, "Net3.inp")
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.energy.global_efficiency = 75  # 75%
        self.wn.options.energy.global_price = 3.61e-8  # $/J; equal to $0.13/kW-h
        self.wn.options.time.hydraulic_timestep = 15*60
        self.wn.options.time.quality_timestep = 15*60
        self.wn.options.time.report_timestep = 15*60
        
    @classmethod
    def tearDownClass(self):
        pass

    def test_energy_report(self):

        sim = self.wntr.sim.EpanetSimulator(self.wn)
        results = sim.run_sim()

        flowrate = results.link["flowrate"].loc[:, self.wn.pump_name_list]
        head = results.node["head"].loc[:, self.wn.node_name_list]
        pump_energy = self.wntr.metrics.pump_energy(flowrate, head, self.wn)

        pump_status = results.link["status"].loc[:, self.wn.pump_name_list]
        utilization = pump_status.mean() * 100

        timestep = self.wn.options.time.report_timestep
        total_pumped_volume_Mgal = (flowrate * timestep * 264.172 / 1e6).sum()
        pump_energy_kWhr = pump_energy / (1000 * 3600)
        total_pump_energy_kWhr = pump_energy_kWhr.sum()
        energy_per_vol = total_pump_energy_kWhr / total_pumped_volume_Mgal  # kW-hr/Mgal

        pump_power_kW = pump_energy_kWhr / (timestep / 3600)
        average_power = {}
        for pump in pump_power_kW.columns:
            average_power[pump] = pump_power_kW.loc[pump_status[pump] == 1, pump].mean()
        average_power = pd.Series(average_power)

        peak_power = pump_power_kW.max()

        pump_cost = self.wntr.metrics.pump_cost(pump_energy, self.wn)
        cost_per_day = pump_cost.sum() / 7  # pump energy (J) * cost ($/J)

        # Compare results to an Energy Report from EPANET GUI (setting global price to $0.13)
        results = pd.DataFrame(index=["10", "335"])
        results["utilization"] = utilization
        results["energy_per_vol"] = energy_per_vol
        results["average_power"] = average_power
        results["peak_power"] = peak_power
        results["cost_per_day"] = cost_per_day

        solution = {
            "utilization": [58.33, 23.60],
            "energy_per_vol": [313.71, 394.29],
            "average_power": [62.05, 309.41],
            "peak_power": [62.76, 310.84],
            "cost_per_day": [112.93, 227.85],
        }
        solution = pd.DataFrame(solution, index=["10", "335"])

        error = abs(results - solution) / solution

        self.assertLess(error.max().max(), 0.01)


if __name__ == "__main__":
    unittest.main()
