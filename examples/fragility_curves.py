import wntr
from scipy.stats import lognorm
import numpy as np
import matplotlib.pylab as plt

np.random.seed(12343)

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Define the earthquake
wn.scale_node_coordinates(1000)
epicenter = (32000,15000) # x,y location
magnitude = 7 # Richter scale
depth = 10000 # m, shallow depth
earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)

# Compute PGA
R = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pipe)
pga = earthquake.pga_attenuation_model(R)  
wntr.network.draw_graph(wn, link_attribute=pga,title='PGA')
  
# Define fragility curve  
FC = wntr.scenario.FragilityCurve()
FC.add_state('Minor', 1, {'Default': lognorm(0.5,scale=0.3)})
FC.add_state('Major', 2, {'Default': lognorm(0.5,scale=0.7)}) 
plt.figure()
plt.title('Fragility curve')
x = np.linspace(0,1,100)
for name, state in FC.states():
    dist=state.distribution['Default']
    plt.plot(x,dist.cdf(x), label=name)
plt.ylim((0,1))
plt.xlabel('PGA')
plt.ylabel('Probability of exceeding a damage state')
plt.legend()

# Draw damage state for each pipe
pipe_PEDS = FC.cdf_probability(pga)
pipe_damage_state = FC.sample_damage_state(pipe_PEDS)
pipe_damage_state_map = FC.get_priority_map()
val = pipe_damage_state.map(pipe_damage_state_map)
wntr.network.draw_graph(wn, link_attribute=val,
                        title='Damage state, 0 = None, 1 = Minor, 2 = Major')
