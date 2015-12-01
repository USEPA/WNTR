import wntr
from scipy.stats import lognorm, expon
import numpy as np
import pandas as pd
import matplotlib.pylab as plt

np.random.seed(12345)

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Define the earthquake
wn.scale_node_coordinates(1000)
epicenter = (32000,15000) # x,y location
magnitude = 5 # Richter scale
depth = 10000 # m, shallow depth
earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)

# Pipe damage based on pga
R = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pipe)
pga = earthquake.pga_attenuation_model(R)      
pipe_FC = wntr.scenario.FragilityCurve()
pipe_FC.add_state('Minor leak', 1, {'Default': lognorm(0.84,scale=0.85),
                                    '121': lognorm(1.35,scale=0.65)})
pipe_FC.add_state('Major leak', 2, {'Default': lognorm(0.84,scale=1.2)}) 
plt.figure()
plt.title('Major/Minor leak thresholds for PGA')
x = np.linspace(0,1,100)
for name, state in pipe_FC.states():
    dist=state.distribution['Default']
    plt.plot(x,dist.cdf(x), label=name)
plt.ylim((0,1))
plt.legend()

pipe_PEDS = pipe_FC.cdf_probability(pga)
pipe_damage_state = pipe_FC.sample_damage_state(pipe_PEDS)

pipe_damage_state_map = pipe_FC.get_priority_map()
wntr.network.draw_graph(wn, link_attribute=pipe_damage_state.map(pipe_damage_state_map),title='Probability of Leakage')

# OR pipe damage based on pgv, RR, L, correction factor
# Correction factor, based on Isoyama et al., 2000
# also see table 4-5 and 4-6  ALA, 2001 Part 1
pipe_characteristics = pd.read_excel('Net3_characteristics.xlsx', 'Pipe')
C = earthquake.correction_factor(pipe_characteristics)
pgv = earthquake.pgv_attenuation_model(R)
RR = earthquake.repair_rate_model(pgv, C)
L = pd.Series(wn.query_link_attribute('length', link_type = wntr.network.Pipe))
pipe_FC2 = wntr.scenario.FragilityCurve()
pipe_FC2.add_state('Minor leak', 1, {'Default': expon(scale=0.2)})
pipe_FC2.add_state('Major leak', 2, {'Default': expon()})
plt.figure()
plt.title('Major/Minor leak thresholds for PGV')
x = np.linspace(0,0.1,100)
for name, state in pipe_FC2.states():
    dist=state.distribution['Default']
    plt.plot(x,dist.cdf(x), label=name)
plt.ylim((0,1))
plt.legend()

pipe_PEDS2 = pipe_FC2.cdf_probability(RR*L)
pipe_damage_state2 = pipe_FC2.sample_damage_state(pipe_PEDS2)

wntr.network.draw_graph(wn, link_attribute=RR*L, link_width=2, link_range = [0, 0.01],title='Probability of Leakage')

pipe_damage_state_map2 = pipe_FC2.get_priority_map()
wntr.network.draw_graph(wn, link_attribute=pipe_damage_state2.map(pipe_damage_state_map2),title='Damage State Map')

# Tank damage
R = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Tank)
pga = earthquake.pga_attenuation_model(R)    
tank_FC = wntr.scenario.FragilityCurve()
# Table 5-3 in ALA, 2001 Part 1 (All tanks)
tank_FC.add_state('DS>=2', 1, {'Default': lognorm(0.8,scale=0.38)})
tank_FC.add_state('DS>=3', 2, {'Default': lognorm(0.8,scale=0.86)})
tank_FC.add_state('DS>=4', 3, {'Default': lognorm(0.61,scale=1.18)})
tank_FC.add_state('DS=5', 4, {'Default': lognorm(0.07,scale=1.16)})
plt.figure()
plt.title('Tank damage state based on PGA')
x = np.linspace(0,4,100)
for name, state in tank_FC.states():
    dist=state.distribution['Default']
    plt.plot(x,dist.cdf(x), label=name)
plt.ylim((0,1))
plt.legend()

tank_PEDS = tank_FC.cdf_probability(pga)
tank_damage_state = tank_FC.sample_damage_state(tank_PEDS)

tank_damage_state_map = tank_FC.get_priority_map()
wntr.network.draw_graph(wn, node_attribute=tank_damage_state.map(tank_damage_state_map), node_size=30,title='Tank Damage State')

# Pump damage
R = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pump)
pga = earthquake.pga_attenuation_model(R)    
pump_FC = wntr.scenario.FragilityCurve()
pump_FC.add_state('Shutoff', 1, {'Default': lognorm(1.35,scale=0.65)})
plt.figure()
plt.title('Shutoff threshold for pumps based on PGA')
x = np.linspace(0,1,100)
for name, state in pump_FC.states():
    dist=state.distribution['Default']
    plt.plot(x,dist.cdf(x), label=name)
plt.ylim((0,1))
plt.legend()

pump_PEDS = pump_FC.cdf_probability(pga)
pump_damage_state = pump_FC.sample_damage_state(pump_PEDS)  

pump_damage_state_map = pump_FC.get_priority_map()
wntr.network.draw_graph(wn, link_attribute=pump_damage_state.map(pump_damage_state_map), link_width=2,title='Pump damage state map')
