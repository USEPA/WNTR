"""
The following example uses WNTR with Chama (https://chama.readthedocs.io) to 
optimize the placement of sensors that minimizes detection time. 
In this example, simulation data is extracted from trace simulations.  
This data could also be extracted from contaminant injection simulations 
and could be translated into other metrics (e.g. extent of 
contamination or population impacted).  Each junction is defined as a feasible
sensor location and the impact formulation is used to optimize sensor placement.
"""
import numpy as np
import pandas as pd
import matplotlib.pylab as plt
import chama
import wntr

# Create a water network model
inp_file = 'networks/Net1.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Run trace simulations (one from each junction) and extract data needed for 
# sensor placement optimization. You can run this step once, save the data to a 
# file, and reload the file for sensor placement
scenario_names = wn.junction_name_list
sim = wntr.sim.EpanetSimulator(wn)
sim.run_sim(save_hyd = True)
wn.options.quality.mode = 'TRACE'
signal = pd.DataFrame()
for inj_node in scenario_names:
    print(inj_node)
    wn.options.quality.trace_node = inj_node
    sim_results = sim.run_sim(use_hyd = True)
    trace = sim_results.node['quality']
    trace = trace.stack()
    trace = trace.reset_index()
    trace.columns = ['T', 'Node', inj_node]
    signal = signal.combine_first(trace)
signal.to_csv('signal.csv')

# Define feasible sensors using location, sample times, and detection threshold
sensor_names = wn.junction_name_list
sample_times = np.arange(0, wn.options.time.duration, wn.options.time.hydraulic_timestep)
threshold = 20
sensors = {}
for location in sensor_names:
    position = chama.sensors.Stationary(location)
    detector = chama.sensors.Point(threshold, sample_times)
    stationary_pt_sensor = chama.sensors.Sensor(position, detector)
    sensors[location] = stationary_pt_sensor

# Extract minimum detection time for each scenario-sensor pair
det_times = chama.impact.extract_detection_times(signal, sensors)
det_time_stats = chama.impact.detection_time_stats(det_times)
min_det_time = det_time_stats[['Scenario','Sensor','Min']]
min_det_time.rename(columns = {'Min':'Impact'}, inplace = True)

# Run sensor placement optimization to minimize detection time using 0 to 5 sensors
#   The impact for undetected scenarios is set at 1.5x the max sample time
#   Sensor cost is defined uniformly using a value of 1.  This means that
#   sensor_budget is equal to the number of sensors to place
impactform = chama.optimize.ImpactFormulation()
scenario_characteristics = pd.DataFrame({'Scenario': scenario_names,
                                         'Undetected Impact': sample_times.max()*1.5})
sensor_characteristics = pd.DataFrame({'Sensor': sensor_names,'Cost': 1})
sensor_budget = [0,1,2,3,4,5]
results = {}
for n in sensor_budget:
    impactform = chama.optimize.ImpactFormulation()
    coveragform = chama.optimize.CoverageFormulation()
    results[n] = impactform.solve(min_det_time, sensor_characteristics, 
                                  scenario_characteristics, n)

# Plot objective for each sensor placement
objective_values =[results[n]['Objective']/3600 for n in sensor_budget]
fig, ax1 = plt.subplots()
ax2 = ax1.twinx() 
ax1.plot(sensor_budget, objective_values, 'b', marker='.')
ax1.set_xlabel('Number of sensors')
ax1.set_ylabel('Expected time to detection (hr)')

# Plot selected sensors, when using 3 sensors
n = 3
selected_sensors = results[n]['Sensors']
wntr.graphics.plot_network(wn, node_attribute=selected_sensors, 
                           title='Selected sensors, n = 3')

# Plot detection time for each scenario, when using 3 sensors
assessment = results[n]['Assessment']
assessment.set_index('Scenario', inplace=True)
wntr.graphics.plot_network(wn, node_attribute=assessment['Impact']/3600, 
                           title='Detection time (hr), n = 3')
