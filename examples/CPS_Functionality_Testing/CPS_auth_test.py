"""
The following test shows the basic functionality of the CPS_Node features of the WNTR+CPS module.
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU

# Create a water network model
inp_file = '../networks/Net3.inp'
wn_controller = wntr.network.WaterNetworkModel(inp_file)
wn_controller_auth = wntr.network.WaterNetworkModel(inp_file)
i=0
for control_name, control in wn_controller._controls.items():
            print(control_name + " : " + control.__str__())
            #print(control.__str__())
            control_assign = wn_controller.get_control(control_name)
            if(i<13):
                control_assign.assign_cps("PLC1") #does not create an actual CPS node by the name of SCADA1, simply creates a label which can be used as reference against the CPS control node registry
                #wn_controller.assign_control_to_cps_node(self, control, "PLC1")
            else:
                control_assign.assign_cps("PLC2")
            i+=1
i=0
for control_name, control in wn_controller_auth._controls.items():
            #print(control_name + " : " + control.__str__())
            #print(control.__str__())
            control_assign = wn_controller_auth.get_control(control_name)
            if(i<13):
                control_assign.assign_cps("PLC1") #does not create an actual CPS node by the name of SCADA1, simply creates a label which can be used as reference against the CPS control node registry
                #wn_controller_auth.assign_control_to_cps_node(self, control, "PLC1")
            else:
                control_assign.assign_cps("PLC2")
            i+=1
            
wn_controller._cps_reg.add_PLC("PLC1")
wn_controller._cps_reg.add_PLC("PLC2")
wn_controller._cps_reg.add_SCADA("SCADA1")
wn_controller._cps_reg["SCADA1"].add_owned("PLC1")
wn_controller._cps_reg["SCADA1"].add_owned("PLC2")
wn_controller._cps_reg["PLC1"].add_owner("SCADA1")
wn_controller._cps_reg["PLC2"].add_owner("SCADA1")
wn_controller_auth._cps_reg.add_PLC("PLC1")
wn_controller_auth._cps_reg.add_PLC("PLC2")
wn_controller_auth._cps_reg.add_SCADA("SCADA1")
wn_controller_auth._cps_reg["SCADA1"].add_owned("PLC1")
wn_controller_auth._cps_reg["SCADA1"].add_owned("PLC2")
wn_controller_auth._cps_reg["PLC1"].add_owner("SCADA1")
wn_controller_auth._cps_reg["PLC2"].add_owner("SCADA1")

wn_controller_auth._cps_reg["PLC1"].add_owned("PLC2")

# Test authority hierarchy via control changes 
wn_controller._cps_reg["SCADA1"].change_control("IF SYSTEM TIME IS 97:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3","control 9", "Link 10 OPEN AT TIME 98", "control 9")
wn_controller_auth._cps_reg["SCADA1"].change_control("IF SYSTEM TIME IS 97:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3","control 9", "Link 10 OPEN AT TIME 98", "control 9")
wn_controller._cps_reg["PLC1"].change_control("IF SYSTEM TIME IS 98:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3","control 9", "Link 10 OPEN AT TIME 97", "control 9")
wn_controller_auth._cps_reg["PLC1"].change_control("IF SYSTEM TIME IS 98:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3","control 9", "Link 10 OPEN AT TIME 97", "control 9")
# This command should work
#wn_controller_auth._cps_reg["PLC1"].change_control("IF TANK 1 LEVEL BELOW 5.21208 THEN PUMP 335 STATUS IS OPEN PRIORITY 3","control 15", "Link 335 OPEN IF Node 1 BELOW 17.2", "control 15")
# This command should fail
wn_controller._cps_reg["PLC1"].change_control("IF TANK 1 LEVEL BELOW 5.21208 THEN PUMP 335 STATUS IS OPEN PRIORITY 3","control 15", "Link 335 OPEN IF Node 1 BELOW 17.2", "control 15")

# Simulate hydraulics
sim_1 = wntr.sim.EpanetSimulator(wn_controller)
results_1 = sim_1.run_sim()
sim_2 = wntr.sim.EpanetSimulator(wn_controller_auth)
results_2 = sim_2.run_sim()
diff = results_1.node['pressure'].compare(results_2.node['pressure'])
#print(results_1.node['pressure'])
#print(results_2.node['pressure'])
print(diff)

# Plot results on the network
pressure_at_5hr = results_1.node['pressure'].loc[5*3600, :]
wntr.graphics.plot_network(wn_controller, node_attribute=pressure_at_5hr, node_size=30, 
                        title='Pressure at 5 hours')
