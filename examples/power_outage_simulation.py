import epanetlib as en
import matplotlib.pylab as plt
import numpy as np
from sympy.physics import units

if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa

plt.close('all')

inp_file = 'networks/Net6_mod.inp'
#inp_file = 'networks/Net3.inp'

# Create water network model from inp file
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)


nHours = 23
wn.time_options['DURATION'] = nHours*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 3600

# Nominal pressure must be provided for pressure driven analysis
wn.options['NOMINAL PRESSURE'] = 40*float(units.psi/units.waterpressure) # psi to m
wn.options['MINIMUM PRESSURE'] = 0 # Meter head

# Create simulation object of the PYOMO simulator
pyomo_sim = en.sim.PyomoSimulator(wn)

# Define power outage times
#pyomo_sim.all_pump_outage('0 days 02:00:00', '0 days 15:00:00')
pyomo_sim.all_pump_outage('0 days 02:00:00', '6 days 20:00:00')
#pyomo_sim_pdd.add_pump_outage('335', '0 days 02:00:00', '0 days 15:00:00')

# Run simulation
pyomo_results = pyomo_sim.run_sim()

nzd_junctions = wn.query_node_attribute('base_demand', np.greater, 0, node_type=en.network.Junction).keys()
# Percent demand met = actual/expected
powOutage = pyomo_results.node.loc[nzd_junctions, 'demand']/(pyomo_results.node.loc[nzd_junctions, 'expected_demand'])
powOutage = powOutage.unstack().T 
powOutage.index = powOutage.index.format() 

#powOutage.plot(legend=False)
powOutage.mean(axis=1).plot(label='Average', color='k', linewidth=2.0, legend=False)
plt.ylim( (-0.05, 1.05) )
#plt.legend(loc='best')
plt.ylabel('Percent demand met')
plt.title('Network wide power outage')

plt.show()

for tank_name, tank in wn.nodes(en.network.Tank):
    print tank_name, pyomo_results.node['pressure'][tank_name]


# Plot some results
plt.figure()
# Actual demand at all nodes
plt.subplot(2,2,1)
for node_name, node in wn.nodes(en.network.Junction):
    actual_demands = pyomo_results.node['demand'][node_name]
    plt.plot(actual_demands, label=node_name)
#plt.ylim([0, 0.535])
plt.ylabel('Actual Demand (m^3/s)')
plt.xlabel('Time (Hours)')
#plt.legend()
# Expected demand at all nodes
plt.subplot(2,2,3)
for node_name, node in wn.nodes(en.network.Junction):
    expected_demands = pyomo_results.node['expected_demand'][node_name]
    plt.plot(expected_demands, label=node_name)
#plt.ylim([0, 0.535])
plt.ylabel('Expected Demand (m^3/s)')
plt.xlabel('Time (Hours)')
#plt.legend()
plt.show()

# Pressure in the tanks
plt.subplot(2,2,2)
for tank_name, tank in wn.nodes(en.network.Tank):
    tank_pressure = pyomo_results.node['pressure'][tank_name]
    plt.plot(tank_pressure, label=tank_name)
plt.ylim([0, 50])
plt.ylabel('Tank Pressure (m)')
plt.xlabel('Time (Hours)')
plt.legend()
# Pump flow
plt.subplot(2,2,4)
for pump_name, pump in wn.links(en.network.Pump):
    pump_flow = pyomo_results.link['flowrate'][pump_name]
    plt.plot(pump_flow, label=pump_name)
plt.ylim([-0.15, 0.15])
plt.ylabel('Pump Flow (m^3/s)')
plt.xlabel('Time (Hours)')
plt.legend()

plt.show()

#print "Reservoir flow: ", pyomo_results.node['demand']['RESERVOIR-3323']