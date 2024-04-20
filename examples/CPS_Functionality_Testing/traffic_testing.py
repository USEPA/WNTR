"""
The following test is intended to show the functionality of post-hoc traffic generation
Simulation results should be extracted by column and associated with their corresponding CPS nodes and edges, if any
Based on those values and the controls associated, traffic should be generated to suit each timestep
"""
import wntr
from wntr.network.CPS_node import SCADA, PLC, RTU, MODBUS, EIP, SER, CPSNodeRegistry, CPSEdgeRegistry
import wntr.network.io
from wntr.network.controls import ValueCondition, RelativeCondition
import wntr.metrics.topographic
from wntr.network.layer import autogenerate_full_cps_layer
import plotly.express as px


# Create a water network model
inp_file = '../networks/Net3.inp'
wn_controller = wntr.network.WaterNetworkModel(inp_file)
wn_baseline = wntr.network.WaterNetworkModel(inp_file)
# Generate a CPS layer     
autogenerate_full_cps_layer(wn_controller, placement_type='complex', timed_control_assignments='local', edge_types='MODBUS', n=2, s=1, verbose=1)
# Test the CPS layer's connectivity
cpsG = wn_controller.cps_to_graph()
print(wntr.metrics.topographic.algebraic_connectivity(cpsG))
print(wntr.metrics.topographic.spectral_gap(cpsG))
print(wntr.metrics.topographic.terminal_nodes(cpsG))
# Test the water network model 
sim_cps = wntr.sim.EpanetSimulator(wn_controller)
results_cps = sim_cps.run_sim()   
sim_baseline = wntr.sim.EpanetSimulator(wn_baseline)
results_baseline = sim_baseline.run_sim()   
diff = results_baseline.node['pressure'].compare(results_cps.node['pressure'])   
print( results_baseline.node['pressure'].columns )
for ( col in results_baseline.node['pressure'].columns ):
    if (col+'-PLC') in wn_controller._cps_reg:
        print("Found " + col+'-PLC')
 #   print( col )
#print(diff)
