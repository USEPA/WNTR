import unittest
from os.path import abspath, dirname, join

import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))


class TestEpanetUnits(unittest.TestCase):
    def test_Concentration(self):
        typestring = "Concentration"
        data_expected = 1  # kg/m3
        data = 1000  # mg/L
        for flowunit in range(10):
            self.execute_check_qual(typestring, flowunit, data, data_expected)

    def test_Demand(self):
        data_expected = 1.0  # m/s
        for typestring in ["Demand", "Flow"]:
            for flowunit in range(10):
                if flowunit == 0:
                    data = 35.3146667  # ft3/s
                elif flowunit == 1:
                    data = 15850.3231  # gall/min
                elif flowunit == 2:
                    data = 22.8244653  # million gall/d
                elif flowunit == 3:
                    data = 19.0  # million imperial gall/d
                elif flowunit == 4:
                    data = 70.0456199  # acre-feet/day
                elif flowunit == 5:
                    data = 1000.0  # L/s
                elif flowunit == 6:
                    data = 60000.0  # L/min
                elif flowunit == 7:
                    data = 86.4  # million L/d
                elif flowunit == 8:
                    data = 3600.0  # m3/h
                elif flowunit == 9:
                    data = 86400.0  # m3/d
                self.execute_check(typestring, flowunit, data, data_expected)

    def test_Emitter_Coeff(self):
        data_expected = 1.0  # (m3/s)/sqrt(m)
        typestring = "EmitterCoeff"
        data_expected = 1  # m
        for flowunit in range(10):
            if flowunit == 0:
                data = 35.3146667  # ft3/s
            elif flowunit == 1:
                data = 15850.3231  # gall/min
            elif flowunit == 2:
                data = 22.8244653  # million gall/d
            elif flowunit == 3:
                data = 19.0  # million imperial gall/d
            elif flowunit == 4:
                data = 70.0456199  # acre-feet/day
            elif flowunit == 5:
                data = 1000.0  # L/s
            elif flowunit == 6:
                data = 60000.0  # L/min
            elif flowunit == 7:
                data = 86.4  # million L/d
            elif flowunit == 8:
                data = 3600.0  # m3/h
            elif flowunit == 9:
                data = 86400.0  # m3/d

            if flowunit in [0, 1, 2, 3, 4]:
                data = data/np.sqrt(1.421970206324753)  # flowrate/sqrt(psi)
            else:
                data = data # flowrate/sqrt(m)
                
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Pipe_Diameter(self):
        typestring = "PipeDiameter"
        data_expected = 1.0  # m
        for flowunit in range(10):
            if flowunit in [0, 1, 2, 3, 4]:
                data = 39.3701  # in
            elif flowunit in [5, 6, 7, 8, 9]:
                data = 1000  # mm
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Length(self):
        data_expected = 1.0  # m
        for typestring in ["TankDiameter", "Elevation", "HydraulicHead", "Length"]:
            for flowunit in range(10):
                if flowunit in [0, 1, 2, 3, 4]:
                    data = 3.28084  # ft
                elif flowunit in [5, 6, 7, 8, 9]:
                    data = 1  # m
                self.execute_check(typestring, flowunit, data, data_expected)

    def test_Velocity(self):
        typestring = "Velocity"
        data_expected = 1.0  # m/s
        for flowunit in range(10):
            if flowunit in [0, 1, 2, 3, 4]:
                data = 3.28084  # ft/s
            elif flowunit in [5, 6, 7, 8, 9]:
                data = 1  # m/s
            self.execute_check(typestring, flowunit, data, data_expected)

        # test list
        data = np.array([10, 20, 30])  # ft/s
        data_expected = [3.048, 6.096, 9.144]  # m/s
        self.execute_check_list(typestring, 1, data, data_expected)

    def test_Energy(self):
        typestring = "Energy"
        data_expected = 1000000  # J
        data = 0.277777777778  # kW*hr
        for flowunit in range(10):
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Power(self):
        typestring = "Power"
        data_expected = 1000  # W
        for flowunit in range(10):
            if flowunit in [0, 1, 2, 3, 4]:
                data = 1.34102209  # hp
            elif flowunit in [5, 6, 7, 8, 9]:
                data = 1  # kW
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Pressure(self):
        typestring = "Pressure"
        data_expected = 1  # m
        for flowunit in range(10):
            if flowunit in [0, 1, 2, 3, 4]:
                data = 1.421970206324753  # psi
            elif flowunit in [5, 6, 7, 8, 9]:
                data = 1  # m
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Source_Mass_Injection(self):
        typestring = "SourceMassInject"
        data_expected = 1  # kg/s
        data = 6.0e7  # mg/min
        for flowunit in range(10):
            self.execute_check_qual(typestring, flowunit, data, data_expected)

    def test_Volume(self):
        typestring = "Volume"
        data_expected = 1  # m3
        for flowunit in range(10):
            if flowunit in [0, 1, 2, 3, 4]:
                data = 35.3147  # ft3
            elif flowunit in [5, 6, 7, 8, 9]:
                data = 1  # m3
            self.execute_check(typestring, flowunit, data, data_expected)

    def test_Water_Age(self):
        typestring = "WaterAge"
        data_expected = 1  # s
        data = 0.000277778  # hr
        for flowunit in range(10):
            self.execute_check_qual(typestring, flowunit, data, data_expected)

    def execute_check(self, typestring, flowunit, data, data_expected):
        #    data_convert = wntr.utils.convert(typestring, flowunit, data)
        data_convert = wntr.epanet.util.HydParam[typestring]._to_si(
            wntr.epanet.util.FlowUnits(flowunit), data
        )
        self.assertLess(
            abs((data_convert - data_expected) / float(data_expected)), 0.001
        )
        data_convert = wntr.epanet.util.HydParam[typestring]._from_si(
            wntr.epanet.util.FlowUnits(flowunit), data_expected
        )
        self.assertLess(abs((data_convert - data) / data), 0.001)

    def execute_check_list(self, typestring, flowunit, data, data_expected):
        #    data_convert = wntr.utils.convert(typestring, flowunit, data)
        data_convert = wntr.epanet.util.HydParam[typestring]._to_si(
            wntr.epanet.util.FlowUnits(flowunit), data
        )
        data_convert = [round(k, 3) for k in data_convert]
        self.assertListEqual(data_convert, data_expected)

    def execute_check_qual(self, typestring, flowunit, data, data_expected):
        #    data_convert = wntr.utils.convert(typestring, flowunit, data)
        data_convert = wntr.epanet.util.QualParam[typestring]._to_si(
            wntr.epanet.util.FlowUnits(flowunit), data
        )
        self.assertLess(
            abs((data_convert - data_expected) / float(data_expected)), 0.001
        )
        data_convert = wntr.epanet.util.QualParam[typestring]._from_si(
            wntr.epanet.util.FlowUnits(flowunit), data_expected
        )
        self.assertLess(abs((data_convert - data) / data), 0.001)

    def execute_check_qual_list(self, typestring, flowunit, data, data_expected):
        #    data_convert = wntr.utils.convert(typestring, flowunit, data)
        data_convert = wntr.epanet.util.QualParam[typestring]._to_si(
            wntr.epanet.util.FlowUnits(flowunit), data
        )
        data_convert = [round(k, 3) for k in data_convert]
        self.assertListEqual(data_convert, data_expected)


if __name__ == "__main__":
    unittest.main()
