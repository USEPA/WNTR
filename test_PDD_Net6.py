import epanetlib as en
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units
import time
import networkx as nx
import pandas as pd

# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart

plt.close('all')

inp_file = 'networks/Net6_mod.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

nHours = 24
wn.time_options['DURATION'] = nHours*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 3600

# Run a demand driven simulation and store results
pyomo_sim = en.sim.PyomoSimulator(wn,'DEMAND DRIVEN')
print '\nRunning Demand Driven Simulation'
res_demand_driven = pyomo_sim.run_sim()

# Betweeness Centrality at different times
attr = res_demand_driven.link.loc[(slice(None), pd.Timedelta(hours =  6)), 'flowrate']
G_flowrate = wn.get_weighted_graph_copy(link_attribute=attr)
bet_cen = nx.betweenness_centrality(G_flowrate)
bet_cen_trim_6 = dict([(k1,v) for k1,v in bet_cen.iteritems() if v > 0.01])
en.network.draw_graph(wn, node_attribute=bet_cen_trim_6, title='Betweenness Centrality, 6 AM', node_size=40)

attr = res_demand_driven.link.loc[(slice(None), pd.Timedelta(hours =  12)), 'flowrate']
G_flowrate = wn.get_weighted_graph_copy(link_attribute=attr)
bet_cen = nx.betweenness_centrality(G_flowrate)
bet_cen_trim_12 = dict([(k1,v) for k1,v in bet_cen.iteritems() if v > 0.01])
en.network.draw_graph(wn, node_attribute=bet_cen_trim_12, title='Betweenness Centrality, 12 PM', node_size=40)

attr = res_demand_driven.link.loc[(slice(None), pd.Timedelta(hours =  20)), 'flowrate']
G_flowrate = wn.get_weighted_graph_copy(link_attribute=attr)
bet_cen = nx.betweenness_centrality(G_flowrate)
bet_cen_trim_20 = dict([(k1,v) for k1,v in bet_cen.iteritems() if v > 0.01])
en.network.draw_graph(wn, node_attribute=bet_cen_trim_20, title='Betweenness Centrality, 8 PM', node_size=40)

    
# Add options and conditional controls for PDD
wn.options['MINIMUM PRESSURE'] = 0 # m
#wn.options['NOMINAL PRESSURE'] = 40*float(units.psi/units.waterpressure) # psi to m
wn.set_nominal_pressures(res = res_demand_driven)

# Modify demand patterns
pat0 = wn.get_pattern('PATTERN-0') # Residential
pat1 = wn.get_pattern('PATTERN-1') # Constant
pat2 = [0.1, 0.1, 0.1, 0.1, 0.1, 0.12, 0.16, 0.416, 0.68, 0.736, 0.8, 0.8, 0.8, 0.8, 0.76, 0.72, 0.64, 0.32, 0.176, 0.104, 0.1, 0.1, 0.1, 0.1] # Commercial
wn.add_pattern('PATTERN-0', [v*1.0 for v in pat0]) 
wn.add_pattern('PATTERN-1', [v*1.0 for v in pat1])
wn.add_pattern('PATTERN-2', [v*1.0 for v in pat2])
count = 0
np.random.seed(12345)
pattern = dict([(node_name, 2) for node_name, node in wn.nodes(en.network.Junction)])
pipe_list = [link_name for link_name, link in wn.links(en.network.Pipe)]
for node_name, node in wn.nodes(en.network.Junction):
    
    links = wn.get_links_for_node(node._name)
    max_diameter = 0
    for link_name in links:
        if link_name in pipe_list:
            link = wn.get_link(link_name)
            max_diameter = max(max_diameter, link.diameter)
    if max_diameter <= 16*float(units.inch/units.meter):
        count = count + 1
        node.demand_pattern_name = 'PATTERN-0' # residential under 16 in
        pattern[node_name] = 0
    
    if np.random.rand() < 0.1:
        node.demand_pattern_name = 'PATTERN-1' # uniform pattern
        pattern[node_name] = 1
        
print "Percent residential nodes: " + str(float(count)/wn._num_junctions)
pipes = dict([(link_name, 1) for link_name, link in wn.links()])
pipes_16plus = wn.query_link_attribute('diameter', np.greater, 16*float(units.inch/units.meter)).keys()
for k in pipes_16plus:
    pipes[k] = 2
en.network.draw_graph(wn, link_attribute=pipes, link_width=pipes, node_size=0)
en.network.draw_graph(wn, node_attribute=pattern, link_attribute=pipes, link_width=pipes, node_size=40)

plt.figure()
plt.plot(wn.get_pattern('PATTERN-0'), label='Residential')
plt.hold(True)
plt.plot(wn.get_pattern('PATTERN-1'), label='Constant')
plt.hold(True)
plt.plot(wn.get_pattern('PATTERN-2'), label='Commercial')
plt.legend()

expected_demand = {}
for node_name, node in wn.nodes(en.network.Junction):
    if node.demand_pattern_name:
        expected_demand[node_name] = sum(node.base_demand*wn.time_options['HYDRAULIC TIMESTEP']*np.array(wn.get_pattern(node.demand_pattern_name)))
    else:
        expected_demand[node_name] = sum(node.base_demand*wn.time_options['HYDRAULIC TIMESTEP'])
tank_capacity = {}
for tank_name, tank in wn.nodes(en.network.Tank):
    tank_capacity[tank_name] = np.pi*(tank.diameter/2)**2*(tank.max_level - tank.min_level)
print "Total daily demand: " + str(sum(expected_demand.values()))
print "Total tank capacity: " + str(sum(tank_capacity.values()))
print "Ratio: " + str(sum(expected_demand.values())/sum(tank_capacity.values()))

# Net 6 has 61 pumps, at 22 unique locations
pump_stations = {
    '1': ['PUMP-3829'], # Controls TANK-3326
    '2': ['PUMP-3830', 'PUMP-3831', 'PUMP-3832', 'PUMP-3833', 'PUMP-3834'], #  Controls TANK-3325, Pump station 2 is connected to the reservoir
    '3': ['PUMP-3835', 'PUMP-3836', 'PUMP-3837', 'PUMP-3838'], # Controls TANK-3333
    '4': ['PUMP-3839', 'PUMP-3840', 'PUMP-3841'], # Controls TANK-3333
    '5': ['PUMP-3842', 'PUMP-3843', 'PUMP-3844'], # Controls TANK-3335
    '6': ['PUMP-3845', 'PUMP-3846'], # Controls TANK-3336
    '7': ['PUMP-3847', 'PUMP-3848'], # Controls TANK-3337
    '8': ['PUMP-3849', 'PUMP-3850', 'PUMP-3851', 'PUMP-3852', 'PUMP-3853'], # Controls TANK-3337
    '9': ['PUMP-3854', 'PUMP-3855', 'PUMP-3856'], # TANK-3340
    '10': ['PUMP-3857', 'PUMP-3858', 'PUMP-3859'], # Controls TANK-3341
    '11': ['PUMP-3860', 'PUMP-3861', 'PUMP-3862'], # Controls TANK-3342
    '12': ['PUMP-3863', 'PUMP-3864', 'PUMP-3865', 'PUMP-3866'], # Controls TANK-3343
    '13': ['PUMP-3867', 'PUMP-3868', 'PUMP-3869'], # Controls TANK-3346
    '14': ['PUMP-3870', 'PUMP-3871'], # Controls TANK-3347
    '15': ['PUMP-3872', 'PUMP-3873', 'PUMP-3874'], # Controls TANK-3349
    '16': ['PUMP-3875', 'PUMP-3876', 'PUMP-3877'], # Controls TANK-3348
    '17': ['PUMP-3878'], # Controls TANK-3352
    '18': ['PUMP-3879', 'PUMP-3880', 'PUMP-3881'], # Controls TANK-3353
    '19': ['PUMP-3882', 'PUMP-3883', 'PUMP-3884'], # Controls TANK-3355
    '20': ['PUMP-3885'], # Controls TANK-3354
    '21': ['PUMP-3886', 'PUMP-3887', 'PUMP-3888'], # Controls TANK-3356
    '22': ['PUMP-3889']} # No curve, only power 15?
    # LINK-1827 controls TANK-3324

associated_tank = {
    '1': ['TANK-3326'],
    '2': ['TANK-3325'],
    '3': ['TANK-3333'],
    '4': ['TANK-3333'],
    '5': ['TANK-3335'],
    '6': ['TANK-3336'],
    '7': ['TANK-3337'],
    '8': ['TANK-3337'],
    '9': ['TANK-3340'],
    '10': ['TANK-3341'],
    '11': ['TANK-3342'],
    '12': ['TANK-3343'],
    '13': ['TANK-3346'],
    '14': ['TANK-3347'],
    '15': ['TANK-3349'],
    '16': ['TANK-3348'],
    '17': ['TANK-3352'],
    '18': ['TANK-3353'],
    '19': ['TANK-3355'],
    '20': ['TANK-3354'],
    '21': ['TANK-3356'],
    '22': []} 


# Create a plot connecting pumps to associated tanks
#tank_path = dict([(link_name, 1) for link_name, link in wn.links()])
#tank_path_color = dict([(link_name, 1) for link_name, link in wn.links()])
#pump_nodes = dict([(link.end_node(), 1) for link_name, link in wn.links(en.network.Pump)])
#tank_nodes = dict([(node_name, 2) for node_name, node in wn.nodes(en.network.Tank)])
#pump_tank_nodes = dict(pump_nodes.items() + tank_nodes.items())
#G2 =  wn.get_graph_copy()
#wn2 = wn.copy()
#for k,v in pump_stations.iteritems():
#    link = wn.get_link(v[0])
#    end_node = link.end_node()
#    tank = associated_tank[k]
#    if tank:
#        tank_node = tank[0]
#        G2.add_edge(tank_node, end_node, key=k)
#        wn2.add_pipe(k, tank_node, end_node, status='OPEN')
#        path = nx.shortest_path(G2.to_undirected(), source=end_node, target=tank_node)
#        tank_path[k] = 2 #int(k)+1
#        tank_path_color[k] = 3
#en.network.draw_graph(wn2, node_attribute = pump_tank_nodes, link_attribute=tank_path, link_width=tank_path_color, node_size=40, link_cmap=plt.cm.jet, node_cmap=plt.cm.winter)

start_time = '0 days 2:00:00' # tank levels, pump operations stabalize after noon
end_time = '7 days 00:00:00' 
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, node_type=en.network.Junction).keys()

# Power outage scenarios
pyomo_results = {}
for k,v in pump_stations.iteritems():
    t0 = time.time()
    # Copy the water network and create a sim object
    wn_power = wn.copy()
    pyomo_sim = en.sim.PyomoSimulator(wn_power,'PRESSURE DRIVEN')
    
    #pyomo_sim.all_pump_outage(start_time, end_time)
    # Add power outage
    for pump_name in v:
        pyomo_sim.add_pump_outage(pump_name, start_time, end_time)
        
    # Re-simulate
    pyomo_results[k] = pyomo_sim.run_sim()
    
    t1 = time.time() - t0
    print t1
    
    # Fraction delivered demand, fraction delivered volumne
    fdd = en.metrics.fraction_delivered_demand(pyomo_results[k], None, 1)
    en.network.draw_graph(wn, node_attribute = fdd, node_size=40, title='FDD')
    fdv = en.metrics.fraction_delivered_volume(pyomo_results[k], None)
    en.network.draw_graph(wn, node_attribute = fdv, node_size=40, title='FDV')

    # Percent demand met
    percent_demand_met = pyomo_results[k].node.loc[nzd_junctions, 'demand']/pyomo_results[k].node.loc[nzd_junctions, 'expected_demand']
    attr_percent_demand_met = {}
    for j in nzd_junctions:
        attr_percent_demand_met[j] = percent_demand_met[j].mean()
    en.network.draw_graph(wn, node_attribute=attr_percent_demand_met, node_size=30, node_range=[0,1], title='Average percent demand met.  Power outage at pump ') # + pump_name)
    percent_demand_met = percent_demand_met.unstack().T 
    percent_demand_met.index = percent_demand_met.index.format() 
    plt.figure()
    percent_demand_met.plot(legend=False)
    plt.ylim( (-0.05, 1.05) )
    #plt.legend(loc='best')
    plt.ylabel('Percent demand met')
    plt.title('Power outage')
    
    # Average percent demand met
    average_percent_demand_met = pyomo_results[k].node.loc[nzd_junctions, 'demand'].sum(level=1)/pyomo_results[k].node.loc[nzd_junctions, 'expected_demand'].sum(level=1)
    average_percent_demand_met.index = average_percent_demand_met.index.format() 
    plt.figure()
    average_percent_demand_met.plot(label='Average', color='k', linewidth=2.0, legend=False)
    plt.ylim( (-0.05, 1.05) )
    plt.legend(loc='best')
    plt.ylabel('Average percent demand met')
    plt.title('Power outage')
    
    # Actual demand at all nodes
    plt.figure()
    for node_name, node in wn.nodes(en.network.Junction):
        actual_demands = pyomo_results[k].node['demand'][node_name]
        plt.plot(actual_demands, label=node_name)
    #plt.ylim([0, 0.025])
    plt.ylabel('Actual Demand (m^3/s)')
    plt.xlabel('Time (Hours)')
    #plt.legend()
    
    # Expected demand at all nodes
    plt.figure()
    for node_name, node in wn.nodes(en.network.Junction):
        expected_demands = pyomo_results[k].node['expected_demand'][node_name]
        plt.plot(expected_demands, label=node_name)
    #plt.ylim([0, 0.025])
    plt.ylabel('Expected Demand (m^3/s)')
    plt.xlabel('Time (Hours)')
    #plt.legend()
    
    # pressure at all nodes
    plt.figure()
    for node_name, node in wn.nodes(en.network.Junction):
        expected_demands = pyomo_results[k].node['pressure'][node_name]
        plt.plot(expected_demands, label=node_name)
    #plt.ylim([0, 0.025])
    plt.ylabel('Pressure (m)')
    plt.xlabel('Time (Hours)')
    #plt.legend()
    
    # Pressure in the tanks
    plt.figure()
    for tank_name, tank in wn.nodes(en.network.Tank):
        tank_pressure = pyomo_results[k].node['pressure'][tank_name]
        plt.plot(tank_pressure, label=tank_name)
    #plt.ylim([0, 50])
    plt.ylabel('Tank Pressure (m)')
    plt.xlabel('Time (Hours)')
    #plt.legend()
    
    # Pump flow
    plt.figure()
    for pump_name, pump in wn.links(en.network.Pump):
    #for pump_name in v:
        pump_flow = pyomo_results[k].link['flowrate'][pump_name]
        plt.plot(pump_flow, label=pump_name)
    #plt.ylim([0, 0.05])
    plt.ylabel('Pump Flow (m^3/s)')
    plt.xlabel('Time (Hours)')
    #plt.legend()
    