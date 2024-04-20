"""
The following test shows the automatic generation of a simple cps network for a hydraulic network based on the control set
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU, MODBUS, EIP, SER, CPSNodeRegistry, CPSEdgeRegistry
import wntr.network.io
from wntr.network.controls import ValueCondition, RelativeCondition
import wntr.metrics.topographic
from wntr.network.layer import autogenerate_full_cps_layer
import plotly.express as px


# Create a water network model
inp_file = '../networks/Net6.inp'
wn_control = wntr.network.WaterNetworkModel(inp_file)
wn_event = wntr.network.WaterNetworkModel(inp_file)
# Generate a CPS layer     
autogenerate_full_cps_layer(wn_event, placement_type='complex', timed_control_assignments='local', edge_types='MODBUS', n=2, verbose=1)
# Test the CPS layer's connectivity
cpsG = wn_event.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
# Modify Controls
wn_event._cps_reg["SCADA-HMI"].change_control(" IF TANK TANK-3343 LEVEL BELOW 8.65632 THEN PUMP PUMP-3863 STATUS IS OPEN PRIORITY 3", "control 70", "LINK PUMP-3863 OPEN IF Node TANK-3343 BELOW 9.65632 PRIORITY 6", "control 69")
#wn_event._cps_reg["SCADA-HMI"].change_control("IF SYSTEM TIME IS 98:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3","control 9", "Link 10 OPEN AT TIME 97", "control 9")

# Test the water network model 
sim_cps = wntr.sim.EpanetSimulator(wn_event)
results_cps = sim_cps.run_sim()   
sim_baseline = wntr.sim.EpanetSimulator(wn_control)
results_baseline = sim_baseline.run_sim()   
diff = results_baseline.node['pressure'].compare(results_cps.node['pressure'])   
print(diff)