"""
The following test shows the basic functionality of the CPS_Node features of the WNTR+CPS module.
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU

# Create a water network model
inp_file = '../networks/Net3.inp'
wn_manual = wntr.network.WaterNetworkModel(inp_file)
wn_controller = wntr.network.WaterNetworkModel(inp_file)
for control_name, control in wn_controller._controls.items():
            print(control_name + " " + control.__str__())
control = wn_controller.get_control("control 15")
control.assign_cps("SCADA1") #does not create an actual CPS node by the name of SCADA1, simply creates a label which can be used as reference against the CPS control node registry
wn_controller._cps_reg.add_PLC("SCADA1")


# Graph the network
wntr.graphics.plot_network(wn_manual, title=wn_manual.name)

# Remove control 15
wn_manual.remove_control("control 15")
wn_controller._cps_reg["SCADA1"].disable_control("control 15")

# Simulate hydraulics
sim_1 = wntr.sim.EpanetSimulator(wn_manual)
results_1 = sim_1.run_sim()
sim_2 = wntr.sim.EpanetSimulator(wn_controller)
results_2 = sim_2.run_sim()
diff = results_1.node['pressure'].compare(results_2.node['pressure'])
print(results_1.node['pressure'])
print(results_2.node['pressure'])
print(diff)

# Plot results on the network
pressure_at_5hr = results_1.node['pressure'].loc[5*3600, :]
wntr.graphics.plot_network(wn_controller, node_attribute=pressure_at_5hr, node_size=30, 
                        title='Pressure at 5 hours')
