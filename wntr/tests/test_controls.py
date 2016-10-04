# These tests test controls
import unittest
import sys
from nose import SkipTest
# HACK until wntr is a proper module
# __file__ fails if script is called in different ways on Windows
# __file__ fails if someone does os.chdir() before
# sys.argv[0] also fails because it doesn't not always contains the path
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))


class TestTimeControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/time_controls.inp'
        self.wn = self.wntr.network.WaterNetworkModel(inp_file)
        self.wn.options.report_timestep = 'all'
        for jname, j in self.wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        
        sim = self.wntr.sim.WNTRSimulator(self.wn, pressure_driven=True)
        self.results = sim.run_sim()

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_time_control_open_vs_closed(self):
        res = self.results
        link_res = res.link
        for t in res.time:
            if t < 5*3600 or t >= 10*3600:
                self.assertAlmostEqual(link_res.at['flowrate',t,'pipe2'], 150/3600.0)
                self.assertEqual(link_res.at['status',t,'pipe2'], 1)
            else:
                self.assertAlmostEqual(link_res.at['flowrate',t,'pipe2'], 0.0)
                self.assertEqual(link_res.at['status',t,'pipe2'], 0)


class TestConditionalControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_close_link_by_tank_level(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/conditional_controls_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.report_timestep = 'all'
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven=True)
        results = sim.run_sim()

        activated_flag = False
        count = 0
        node_res = results.node
        link_res = results.link
        for t in results.time:
            if node_res.at['pressure',t,'tank1'] >= 50.0 and not activated_flag:
                activated_flag = True
            if activated_flag:
                self.assertAlmostEqual(link_res.at['flowrate',t,'pump1'], 0.0)
                self.assertEqual(link_res.at['status',t,'pump1'], 0)
                count += 1
            else:
                self.assertGreaterEqual(link_res.at['flowrate',t,'pump1'], 0.0001)
                self.assertEqual(link_res.at['status',t,'pump1'], 1)
        self.assertEqual(activated_flag, True)
        self.assertGreaterEqual(count, 2)

    def test_open_link_by_tank_level(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/conditional_controls_2.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        wn.options.report_timestep = 'all'
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        activated_flag = False
        count = 0 # Used to make sure the link is opened for at least 2 timesteps to make sure the link stays open
        for t in results.time:
            if results.node.at['pressure',t,'tank1'] >= 300.0 and not activated_flag:
                activated_flag = True
            if activated_flag:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'], 0.002)
                self.assertEqual(results.link.at['status',t,'pipe1'], 1)
                count +=1
            else:
                self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)
                self.assertEqual(results.link.at['status',t,'pipe1'], 0)
        self.assertEqual(activated_flag, True)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(results.link.at['status',results.time[0],'pipe1'], 0) # make sure the pipe starts closed
        self.assertLessEqual(results.node.at['pressure',results.time[0],'tank1'],300.0) # make sure the pipe starts closed

class TestTankControls(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_pipe_closed_for_low_level(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/tank_controls_1.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven=True)
        results = sim.run_sim()

        tank_level_dropped_flag = False
        for t in results.time:
            if results.node.at['pressure',t,'tank1'] <= 10.0:
                self.assertLessEqual(results.link.at['flowrate',t,'pipe1'],0.0)
                self.assertEqual(results.link.at['status',t,'pipe1'],0)
                tank_level_dropped_flag = True
        self.assertEqual(tank_level_dropped_flag, True)

    def test_reopen_pipe_after_tank_fills_back_up(self):
        """
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/tank_controls_2.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven=True)
        results = sim.run_sim()

        tank_level_dropped_flag = False
        tank_refilled_flag = False
        for t in results.time:
            if results.node.at['pressure',t,'tank1'] <= 10.0:
                self.assertLessEqual(results.link.at['flowrate',t,'pipe1'],0.0)
                tank_level_dropped_flag = True
            elif results.node.at['pressure',t,'tank1'] > 10.0:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'],0.001)
                if tank_level_dropped_flag:
                    tank_refilled_flag = True
        self.assertEqual(tank_level_dropped_flag, True)
        self.assertEqual(tank_refilled_flag, True)
        """
        raise SkipTest
        self.assertEqual(True, False)
        
class TestValveControls(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_check_valve_closed(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/cv_controls.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        for t in results.link.major_axis:
            self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)

    def test_check_valve_opened(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/cv_controls.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node('tank1')
        tank2 = wn.get_node('tank2')
        tank1_init_level = tank1.init_level
        tank1.init_level = tank2.init_level
        tank2.init_level = tank1_init_level
        tank1.head = tank1.init_level + tank1.elevation
        tank2.head = tank2.init_level + tank2.elevation
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.link.major_axis:
            if results.node.at['head',t,'tank1'] >= results.node.at['head',t,'tank2']:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'], 0.001)
                flag1 = True
            else:
                self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)
                flag2 = True

        self.assertEqual(flag1, True)
        self.assertEqual(flag2, True)

class TestControlCombinations(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        sys.path.remove(resilienceMainDir)

    def test_open_by_time_close_by_condition(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/control_comb.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        control_action = self.wntr.network.ControlAction(wn.get_link('pipe1'), 'status', self.wntr.network.LinkStatus.opened)
        control = self.wntr.network.TimeControl(wn, 6*3600, 'SIM_TIME', False, control_action)
        wn.add_control('open_time_6',control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.link.major_axis:
            if t == 6*3600:
                flag1 = True
            if t > 0 and (results.node.at['head',t-3600,'tank1'] + (results.node.at['demand',t-3600,'tank1']*3600 * 4 / (3.14159 * wn._tanks['tank1'].diameter**2))) <= 30:
                flag1 = False
                flag2 = True
            if flag1 == False:
                self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)
            elif flag1 == True:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'], 0.001)

        self.assertEqual(flag1, False)
        self.assertEqual(flag2, True)

    def test_close_by_condition_open_by_time_stay(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/control_comb.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node('tank1')
        tank1.init_level = 40.0
        tank1.head = tank1.elevation + 40.0
        pipe1 = wn.get_link('pipe1')
        pipe1.status = self.wntr.network.LinkStatus.opened
        control_action = self.wntr.network.ControlAction(wn.get_link('pipe1'), 'status', self.wntr.network.LinkStatus.opened)
        control = self.wntr.network.TimeControl(wn, 19*3600, 'SIM_TIME', False, control_action)
        wn.add_control('open_time_19',control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        flag1 = False
        flag2 = False
        for t in results.link.major_axis:
            if t == 19*3600:
                flag1 = False
            if t > 0 and (results.node.at['head',t-3600,'tank1'] + (results.node.at['demand',t-3600,'tank1']*3600 * 4 / (3.14159 * wn._tanks['tank1'].diameter**2))) <= 30:
                flag1 = True
                flag2 = True
            if flag1 == False:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'], 0.001)
            elif flag1 == True:
                self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)

        self.assertEqual(flag1, False)
        self.assertEqual(flag2, True)

    def test_close_by_condition_open_by_time_reclose(self):
        inp_file = resilienceMainDir+'/wntr/tests/networks_for_testing/control_comb.inp'
        wn = self.wntr.network.WaterNetworkModel(inp_file)
        tank1 = wn.get_node('tank1')
        tank1.init_level = 40.0
        tank1.head = tank1.elevation + 40.0
        pipe1 = wn.get_link('pipe1')
        pipe1.status = self.wntr.network.LinkStatus.opened
        control_action = self.wntr.network.ControlAction(wn.get_link('pipe1'), 'status', self.wntr.network.LinkStatus.opened)
        control = self.wntr.network.TimeControl(wn, 5*3600, 'SIM_TIME', False, control_action)
        wn.add_control('open_time_5',control)
        for jname, j in wn.nodes(self.wntr.network.Junction):
            j.minimum_pressure = 0.0
            j.nominal_pressure = 15.0
        sim = self.wntr.sim.WNTRSimulator(wn, pressure_driven = True)
        results = sim.run_sim()

        flag1 = False
        for t in results.link.major_axis:
            if t > 0 and (results.node.at['head',t-3600,'tank1'] + (results.node.at['demand',t-3600,'tank1']*3600 * 4 / (3.14159 * wn._tanks['tank1'].diameter**2))) <= 30.0:
                flag1 = True
            if t==5*3600:
                flag1=False
            if flag1 == False:
                self.assertGreaterEqual(results.link.at['flowrate',t,'pipe1'], 0.001)
            elif flag1 == True:
                self.assertAlmostEqual(results.link.at['flowrate',t,'pipe1'], 0.0)

        self.assertEqual(flag1, True)

if __name__ == '__main__':
    unittest.main()
