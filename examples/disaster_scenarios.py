import wntr
import matplotlib.pyplot as plt

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Earthquake properties
wn.scale_node_coordinates(1000)
epicenter = (32000,15000) # x,y location
magnitude = 6.5 # Richter scale
depth = 10000 # m, shallow depth
earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)
distance = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pipe)
pga = earthquake.pga_attenuation_model(distance)  
pgv = earthquake.pgv_attenuation_model(distance)
repair_rate = earthquake.repair_rate_model(pgv) 
   
# Plot PGA and epicenter
wntr.graphics.plot_network(wn, link_attribute=pga, node_size=0, link_width=1.5, 
                           title='Peak ground acceleration')
plt.scatter(epicenter[0], epicenter[1], s=1000, c='r', marker='*', zorder=2)

# Define a leak at pipe '123'
wn.split_pipe('123', '123_B', '123_leak_node')
leak_node = wn.get_node('123_leak_node')           
leak_node.add_leak(wn, area=0.05, start_time=2*3600, end_time=12*3600)
                          
# Define a power outage at pump '335'
wn.add_pump_outage('335', 5*3600, 10*3600)

# Define fire conditions at node '197'
fire_flow_demand = 0.252 # 4000 gal/min = 0.252 m3/s
fire_start = 10*3600
fire_end = 14*3600
fire_flow_pattern = wntr.network.elements.Pattern.BinaryPattern('fire_flow', 
    step_size=wn.options.time.pattern_timestep, start_time=fire_start, 
    end_time=fire_end, duration=wn.options.time.duration)
node = wn.get_node('197')
node.demands.append( (fire_flow_demand, fire_flow_pattern, 'Fire flow'))
    
# Reduce supply, increase demand
for reservoir_name, reservoir in wn.reservoirs():
    reservoir.expected_head.base_value = reservoir.base_head*0.9
for junction_name, junction in wn.junctions():
    for demand in junction.expected_demand:
        demand.base_value = demand.base_value*1.15
    
# Simulate 
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
sim.run_sim()
