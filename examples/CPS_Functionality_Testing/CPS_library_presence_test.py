"""
The following test shows the basic functionality of the CPS_Node features of the WNTR+CPS module.
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU

# Create a water network model
inp_file = '../networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
for control_name, control in wn._controls.items():
            print(control_name + " " + control.__str__())
control = wn.get_control("control 15")
control.assign_cps("SCADA1") #does not create an actual CPS node by the name of SCADA1, simply creates a label which can be used as reference against the CPS control node registry
wn._cps_reg.add_PLC("SCADA1")
print(control._name)
print(wn._controls["control 15"])

# Graph the network
wntr.graphics.plot_network(wn, title=wn.name)

# Simulate hydraulics
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Plot results on the network
pressure_at_5hr = results.node['pressure'].loc[5*3600, :]
wntr.graphics.plot_network(wn, node_attribute=pressure_at_5hr, node_size=30, 
                        title='Pressure at 5 hours')
