"""
The following test shows a full implementation of basic CPS_Node features of the WNTR+CPS module on the Net3 network file.
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU, MODBUS, EIP, SER, CPSNodeRegistry, CPSEdgeRegistry
import wntr.network.io
import wntr.metrics.topographic
import plotly.express as px
import networkx as nx

# Create a water network model
inp_file = '../networks/Net3.inp'
wn_controller = wntr.network.WaterNetworkModel(inp_file)
wn_baseline = wntr.network.WaterNetworkModel(inp_file)
i = 0
for control_name, control in wn_controller._controls.items():
            print(control_name + " : " + control.__str__())
            #print(control.__str__())
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
wn_controller._cps_reg.add_RTU("RTU1")
wn_controller._cps_reg.add_RTU("RTU2")

wn_controller._cps_edges.add_MODBUS("s1_MOD_p1","SCADA1","PLC1")
wn_controller._cps_edges.add_MODBUS("s1_MOD_p2","SCADA1","PLC2")
#wn_controller._cps_edges.add_EIP("s1_EIP_p1","SCADA1","PLC1")
#wn_controller._cps_edges.add_EIP("s1_EIP_p2","SCADA1","PLC2")
#wn_controller._cps_edges.add_SER("s1_SER_p1","SCADA1","PLC1")
#wn_controller._cps_edges.add_SER("s1_SER_p2","SCADA1","PLC2")
wn_controller._cps_edges.add_SER("r1_SER_p1","RTU1","PLC1")
wn_controller._cps_edges.add_SER("r2_SER_p2","RTU2","PLC2")
#initial graph check
cpsG = wn_controller.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
print(wntr.metrics.topographic.terminal_nodes(cpsG))
print(dict(cpsG.degree()))
#plc-to-plc edge added for duplication/connectivity
wn_controller._cps_edges.add_MODBUS("p1_MOD_p2","PLC1","PLC2")
cpsG = wn_controller.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
print(wntr.metrics.topographic.terminal_nodes(cpsG))
print(dict(cpsG.degree()))
#plc-to-plc remove, add rtu-to-plc duplication
wn_controller._cps_edges.remove_edge("p1_MOD_p2")
wn_controller._cps_edges.add_SER("r1_SER_p2","RTU1","PLC2")
wn_controller._cps_edges.add_SER("r2_SER_p1","RTU2","PLC1")
cpsG = wn_controller.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
print(wntr.metrics.topographic.terminal_nodes(cpsG))
#plc-to-plc edge added for duplication/connectivity, combined with rtu-to-plc duplication
wn_controller._cps_edges.add_MODBUS("p1_MOD_p2","SCADA1","PLC1")
cpsG = wn_controller.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
print(wntr.metrics.topographic.terminal_nodes(cpsG))
# Simulate hydraulics
sim_1 = wntr.sim.EpanetSimulator(wn_controller)
results_1 = sim_1.run_sim()
#sim_baseline = wntr.sim.EpanetSimulator(wn_baseline)
#results_baseline = sim_baseline.run_sim()
#diffbl = results_1.node['pressure'].compare(results_baseline.node['pressure'])
#print("Difference matrix between control removal and baseline activity:")
#print(diffbl)

# Plot results on the network
