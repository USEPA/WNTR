import epanetlib as en
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units

# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
    
plt.close('all')

inp_file = 'networks/Net3.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

nHours = 24
wn.time_options['DURATION'] = nHours*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 3600

# Add options and conditional controls for PDD
wn.options['MINIMUM PRESSURE'] = 0 # m
wn.options['NOMINAL PRESSURE'] = 30*float(units.psi/units.waterpressure) # psi to m 
                                
start_time = '0 days 02:00:00' 
end_time = '0 days 18:00:00' 

# Simulate using Pyomo
pyomo_sim = en.sim.PyomoSimulator(wn)
base_results = pyomo_sim.run_sim()

# Turn off pump 10
wn_power = wn.copy()
pyomo_sim = en.sim.PyomoSimulator(wn_power)
pyomo_sim.add_pump_outage('10', start_time, end_time)
# Re-simulate
results_powOutage10 = pyomo_sim.run_sim()

# Turn off pump 335
wn_power = wn.copy()
pyomo_sim = en.sim.PyomoSimulator(wn_power)
pyomo_sim.add_pump_outage('335', start_time, end_time)
# Re-simulate
results_powOutage335 = pyomo_sim.run_sim()

# Turn off both pumps
wn_power = wn.copy()
pyomo_sim = en.sim.PyomoSimulator(wn_power)
pyomo_sim.all_pump_outage(start_time, end_time)
# Re-simulate
results_powOutage = pyomo_sim.run_sim()

# Plot demand and pressure at NZD nodes
base_results.node['nominal'] = wn.options['NOMINAL PRESSURE']
nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, node_type=en.network.Junction).keys()
ticks = np.arange(0,len(nzd_junctions)*nHours+1,nHours+1)

plt.figure()
plt.subplot(311)
base_results.node.loc[nzd_junctions, 'demand'].plot(label='Base case')
results_powOutage10.node.loc[nzd_junctions, 'demand'].plot(label='Power outage at 10')
results_powOutage335.node.loc[nzd_junctions, 'demand'].plot(label='Power outage at 335')
results_powOutage.node.loc[nzd_junctions, 'demand'].plot(label='Network wide power outage', xticks=ticks)
plt.title('Node demand')
plt.legend()

plt.subplot(312)
base_results.node.loc[nzd_junctions, 'pressure'].plot(label='Base case')
results_powOutage10.node.loc[nzd_junctions, 'pressure'].plot(label='Power outage at 10')
results_powOutage335.node.loc[nzd_junctions, 'pressure'].plot(label='Power outage at 335')
results_powOutage.node.loc[nzd_junctions, 'pressure'].plot(label='Network wide power outage', xticks=ticks)
base_results.node.loc[nzd_junctions, 'nominal'].plot(label='NOMINAL', color='k')
plt.title('Node pressure')
plt.legend()

# Percent demand met = actual/expected
powOutage10 = results_powOutage10.node.loc[nzd_junctions, 'demand']/(results_powOutage10.node.loc[nzd_junctions, 'expected_demand'])
powOutage335 = results_powOutage335.node.loc[nzd_junctions, 'demand']/(results_powOutage335.node.loc[nzd_junctions, 'expected_demand'])
powOutage = results_powOutage.node.loc[nzd_junctions, 'demand']/(results_powOutage.node.loc[nzd_junctions, 'expected_demand'])

plt.subplot(313)
powOutage10.plot(label='Power outage at 10', color='g')
powOutage335.plot(label='Power outage at 335', color='r')
powOutage.plot(label='Network wide power outage', color='c', xticks=ticks)
#plt.ylim( (-0.05, 1.05) )
plt.title('Percent demand met')
plt.legend()

# Network plots
attr_powOutage10 = {}
attr_powOutage335 = {}
attr_powOutage = {}
for j in nzd_junctions:
    attr_powOutage10[j] = powOutage10[j].mean()
    attr_powOutage335[j] = powOutage335[j].mean()
    attr_powOutage[j] = powOutage[j].mean()
en.network.draw_graph(wn, node_attribute=attr_powOutage10, node_size=30, node_range=[0,1], title='Average percent demand met.  Power outage at 10')
en.network.draw_graph(wn, node_attribute=attr_powOutage335, node_size=30, node_range=[0,1], title='Average percent demand met.  Power outage at 335')
en.network.draw_graph(wn, node_attribute=attr_powOutage, node_size=30, node_range=[0,1], title='Average percent demand met.  Network wide power outage scenario')

# Time series plots
powOutage10 = powOutage10.unstack().T 
powOutage10.index = powOutage10.index.format() 
powOutage335 = powOutage335.unstack().T 
powOutage335.index = powOutage335.index.format() 
powOutage = powOutage.unstack().T 
powOutage.index = powOutage.index.format() 

powOutage10.plot(legend=False)
powOutage10.mean(axis=1).plot(label='Average', color='k', linewidth=2.0, legend=False)
#plt.ylim( (-0.05, 1.05) )
#plt.legend(loc='best')
plt.ylabel('Percent demand met')
plt.title('Power outage at 10')

powOutage335.plot(legend=False)
powOutage335.mean(axis=1).plot(label='Average', color='k', linewidth=2.0, legend=False)
#plt.ylim( (-0.05, 1.05) )
#plt.legend(loc='best')
plt.ylabel('Percent demand met')
plt.title('Power outage at 335')

powOutage.plot(legend=False)
powOutage.mean(axis=1).plot(label='Average', color='k', linewidth=2.0, legend=False)
#plt.ylim( (-0.05, 1.05) )
#plt.legend(loc='best')
plt.ylabel('Percent demand met')
plt.title('Network wide power outage')