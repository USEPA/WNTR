"""
The following example uses WNTR to calculate the importance of each large pipe 
in the network by running a series of hydraulic simulations with one pipe 
closed at a time and determining if minimum pressure criterion are met at each 
node.
"""
import numpy as np
import matplotlib.pyplot as plt
import wntr


plt.close('all')


### Create the water network model 
inp_file = './Networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
# Adjust simulation options for criticality analyses
analysis_end_time = 72*3600 
wn.options.time.duration = analysis_end_time
# Adjust water network for criticality analysis
nominal_pressure = 17.57 
pressure_threshold = 14.06 
for name, node in wn.nodes():
    node.nominal_pressure = nominal_pressure
expected_demand = wntr.metrics.expected_demand(wn)
pop = wntr.metrics.population(wn)


summary = {}  
### Run a hydraulic simulation using the original network
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
results = sim.run_sim()
temp = results.node['pressure'].min()
temp = temp[temp < pressure_threshold]
orig = list(temp.index)


### Run criticality simulation for each large diameter pipe.
# This is a hydraulic simulation that closes the pipe after one day and
# finds the nodes that dip below the minimum pressure threshold.
# Only the largest pipes were selected to reduce the runtime of this example.
pipes = wn.query_link_attribute('diameter', np.greater_equal, 30*0.0254, 
                                link_type=wntr.network.model.Pipe)      
pipes = list(pipes.keys())
print('Number of pipes tested: ', str(len(pipes)))
for pipe_name in pipes:
    print('Pipe: ', pipe_name)
    wn = wntr.network.WaterNetworkModel(inp_file)
    wn.options.time.duration = analysis_end_time
    for name, node in wn.nodes():
        node.nominal_pressure = nominal_pressure          
    try:
        pipe = wn.get_link(pipe_name)        
        act = wntr.network.controls.ControlAction(pipe, 'status', wntr.network.LinkStatus.Closed)
        cond = wntr.network.controls.SimTimeCondition(wn, '=', '24:00:00')
        ctrl = wntr.network.controls.Control(cond, act)
        wn.add_control('close pipe ' + pipe_name, ctrl)
        sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
        results = sim.run_sim(solver_options={'MAXITER':500})
        temp = results.node['pressure'].min()
        temp = temp[temp < pressure_threshold]
        summary[pipe_name] = list(temp.index)  
        print('   Complete')
    except Exception as e:
        summary[pipe_name] = e
        print('   Failed')


### Calculate difference between the original and pipe criticality simulations
summary_len = {}
summary_pop = {}
failed_sim = {}
for key, val in summary.items():
    if type(val) is list:
        summary[key] = list(set(val) - set(orig))
        summary_len[key] = len(set(val) - set(orig))
        summary_pop[key] = 0
        for node in summary[key]:
            summary_pop[key] = summary_pop[key] + pop[node]
    else:
        failed_sim[key] = val
     
        
### Plot results         
wntr.graphics.plot_network(wn, node_attribute=orig, 
                           title='Nodes that fall below '+str(pressure_threshold)+' psi during normal operating conditions')
wntr.graphics.plot_network(wn, link_attribute=summary_len, node_size=0, 
                           link_width=2, add_colorbar=False, 
                           title='Number of nodes impacted by low pressure conditions\nfor each pipe closure')
wntr.graphics.plot_network(wn, link_attribute=summary_pop, node_size=0, 
                           link_width=2, add_colorbar=False, 
                           title='Number of people impacted by low pressure conditions\nfor each pipe closure')
# Plot the affected network for the three most critical pipes
sorted_keys = sorted(summary_len, key=summary_len.get)
for i in np.arange(1,4,1):
    pipe_name = sorted_keys[-i]
    fig, ax = plt.subplots(1,1)
    wntr.graphics.plot_network(wn, node_attribute=summary[pipe_name], 
                               node_size=20, link_attribute=[pipe_name],
                               title='Pipe '+pipe_name+' is critical \nfor normal operation of '+str(summary_len[pipe_name])+' nodes', ax=ax)
    