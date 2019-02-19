import wntr
from scipy.stats import lognorm
import numpy as np
import matplotlib.pylab as plt

np.random.seed(12343)

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Define the earthquake
wn = wntr.morph.scale_node_coordinates(wn, 1000)
epicenter = (32000,15000) # x,y location
magnitude = 7 # Richter scale
depth = 10000 # m, shallow depth
earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)

# Compute PGA
R = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pipe)
pga = earthquake.pga_attenuation_model(R)  
wntr.graphics.plot_network(wn, link_attribute=pga,title='Peak Ground Acceleration (g)',
                           node_size=0, link_width=2)
  
# Define fragility curve  
FC = wntr.scenario.FragilityCurve()
FC.add_state('Minor', 1, {'Default': lognorm(0.5,scale=0.3)})
FC.add_state('Major', 2, {'Default': lognorm(0.5,scale=0.7)}) 
wntr.graphics.plot_fragility_curve(FC, xlabel='Peak Ground Acceleration (g)')

# Draw damage state for each pipe
pipe_PEDS = FC.cdf_probability(pga)
pipe_damage_state = FC.sample_damage_state(pipe_PEDS)
pipe_damage_state_map = FC.get_priority_map()
val = pipe_damage_state.map(pipe_damage_state_map)
custom_cmp = wntr.graphics.custom_colormap(3, ['grey', 'royalblue', 'darkorange'])
wntr.graphics.plot_network(wn, link_attribute=val, node_size=0, link_width=2,
                           link_cmap=custom_cmp, title='Damage state: 0=None, 1=Minor, 2=Major')
