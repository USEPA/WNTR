"""
The following test shows a full implementation of basic CPS_Node features of the WNTR+CPS module on the Net3 network file.
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU
import plotly.express as px


# Create a water network model
inp_file = '../networks/Net3.inp'
wn_controller = wntr.network.WaterNetworkModel(inp_file)
wn_baseline = wntr.network.WaterNetworkModel(inp_file)
i = 0
for control_name, control in wn_controller._controls.items():
            print(control_name + " " + control.__str__())
            control_assign = wn_controller.get_control(control_name)
            if(i<13):
                control_assign.assign_cps("PLC1") #does not create an actual CPS node by the name of SCADA1, simply creates a label which can be used as reference against the CPS control node registry
            else:
                control_assign.assign_cps("PLC2")
            i+=1
            
wn_controller._cps_reg.add_PLC("PLC1")
wn_controller._cps_reg.add_PLC("PLC2")
wn_controller._cps_reg.add_SCADA("SCADA1")
wn_controller._cps_reg["SCADA1"].add_owned("PLC1")
wn_controller._cps_reg["SCADA1"].add_owned("PLC2")
#print(wn_controller._cps_reg["SCADA1"]._cps_reg)

wn_controller._cps_reg["SCADA1"].disable_owned("PLC1")
#wn_controller._cps_reg["SCADA1"].disable_control("control 7")
wn_controller._cps_reg["SCADA1"].disable_control("control 15")

# Simulate hydraulics
sim_1 = wntr.sim.EpanetSimulator(wn_controller)
results_1 = sim_1.run_sim()
sim_baseline = wntr.sim.EpanetSimulator(wn_baseline)
results_baseline = sim_baseline.run_sim()
diffbl = results_1.node['pressure'].compare(results_baseline.node['pressure'])
print("Difference matrix between control removal and baseline activity:")
print(diffbl)

# Plot results on the network
pressure_at_77hr = results_1.node['pressure'].loc[77*3600, :]
#wntr.graphics.plot_network(wn_controller, node_attribute=pressure_at_77hr, node_size=30, 
 #                       title='Pressure at 77hr', filename='net3_rule7R15R_77h.png')
baseline_pressure_at_77hr = results_baseline.node['pressure'].loc[77*3600, :]
#wntr.graphics.plot_network(wn_baseline, node_attribute=pressure_at_77hr, node_size=30, 
 #                       title='Pressure at 77hr', filename='net3_baseline_77h.png')

#plotting experiment
pressure1 = results_1.node['pressure'].loc[:,wn_controller.node_name_list]
pressurebase = results_baseline.node['pressure'].loc[:, wn_baseline.node_name_list]
#tankH = tankH * 3.28084 # Convert tank head to ft
pressure1.index /= 3600 # convert time to hours
fig = px.line(pressure1)
fig = fig.update_layout(xaxis_title='Time (hr)', yaxis_title='Pressure (Pa)',
                  template='simple_white', width=650, height=400)
fig.write_html('pressure1.html')

pressurebase.index /= 3600 # convert time to hours
figb = px.line(pressurebase)
figb = figb.update_layout(xaxis_title='Time (hr)', yaxis_title='Pressure (Pa)',
                  template='simple_white', width=650, height=400)
figb.write_html('presurebase.html')