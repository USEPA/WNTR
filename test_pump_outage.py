import epanetlib as en
import matplotlib.pylab as plt

plt.close('all')

inp_file = 'networks/Net1.inp'

# Create water network model from inp file
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

# Nominal pressure must be provided for pressure driven analysis
wn.options['NOMINAL PRESSURE'] = 30 # Meter head
wn.options['MINIMUM PRESSURE'] = 0 # Meter head

# Create simulation object of the PYOMO simulator
pyomo_sim = en.sim.PyomoSimulator(wn)

# Define power outage times
pyomo_sim.all_pump_outage('0 days 02:00:00', '0 days 18:00:00')
#pyomo_sim_pdd.add_pump_outage('335', '0 days 02:00:00', '0 days 15:00:00')

# Run simulation
pyomo_results = pyomo_sim.run_sim()

# Plot some results
plt.figure()
# Actual demand at all nodes
plt.subplot(2,2,1)
for node_name, node in wn.nodes(en.network.Junction):
    actual_demands = pyomo_results.node['demand'][node_name]
    plt.plot(actual_demands, label=node_name)
plt.ylim([0, 0.025])
plt.ylabel('Actual Demand (m^3/s)')
plt.xlabel('Time (Hours)')
plt.legend()
# Expected demand at all nodes
plt.subplot(2,2,3)
for node_name, node in wn.nodes(en.network.Junction):
    expected_demands = pyomo_results.node['expected_demand'][node_name]
    plt.plot(expected_demands, label=node_name)
plt.ylim([0, 0.025])
plt.ylabel('Expected Demand (m^3/s)')
plt.xlabel('Time (Hours)')
plt.legend()
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
plt.ylim([0, 0.05])
plt.ylabel('Pump Flow (m^3/s)')
plt.xlabel('Time (Hours)')
plt.legend()

plt.show()

