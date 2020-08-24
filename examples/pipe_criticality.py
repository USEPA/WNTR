"""
The following example runs a pipe criticality analysis on large diameter pipes
to compute the impact that pipe closures have on pressure in the system.  
The analysis is run using a series of hydraulic simulations with one pipe 
closed at a time and determines if minimum pressure criterion are met 
at each junction.  Note that for many networks, simulations can fail when 
certain pipes are closed. try:except blocks are recommended within the 
simulation loop to catch these instances.
"""
import numpy as np
import wntr

# Create a water network model 
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Adjust simulation options for criticality analyses
analysis_end_time = 72*3600 
wn.options.time.duration = analysis_end_time
nominal_pressure = 17.57 
for name, node in wn.nodes():
    node.nominal_pressure = nominal_pressure

# Create a list of pipes with large diameter to include in the analysis
pipes = wn.query_link_attribute('diameter', np.greater_equal, 24*0.0254, 
                                link_type=wntr.network.model.Pipe)      
pipes = list(pipes.index)
wntr.graphics.plot_network(wn, link_attribute=pipes, 
                           title='Pipes included in criticality analysis')
   
# Define the pressure threshold
pressure_threshold = 14.06 

# Run a preliminary simulation to determine if junctions drop below the 
# pressure threshold during normal conditions
sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
results = sim.run_sim()
min_pressure = results.node['pressure'].loc[:,wn.junction_name_list].min()
below_threshold_normal_conditions = set(min_pressure[min_pressure < pressure_threshold].index)

# Run the criticality analysis, closing one pipe for each simulation
junctions_impacted = {} 
for pipe_name in pipes:
    
    print('Pipe:', pipe_name)     
    
    # Reset the water network model
    wn.reset_initial_values()

    # Add a control to close the pipe
    pipe = wn.get_link(pipe_name)        
    act = wntr.network.controls.ControlAction(pipe, 'status', 
                                              wntr.network.LinkStatus.Closed)
    cond = wntr.network.controls.SimTimeCondition(wn, '=', '24:00:00')
    ctrl = wntr.network.controls.Control(cond, act)
    wn.add_control('close pipe ' + pipe_name, ctrl)
        
    # Run a PDD simulation
    sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
    results = sim.run_sim()
        
    # Extract the number of junctions that dip below the minimum pressure threshold
    min_pressure = results.node['pressure'].loc[:,wn.junction_name_list].min()
    below_threshold = set(min_pressure[min_pressure < pressure_threshold].index)
    
    # Remove the set of junctions that were below the pressure threshold during 
    # normal conditions and store the result
    junctions_impacted[pipe_name] = below_threshold - below_threshold_normal_conditions
        
    # Remove the control
    wn.remove_control('close pipe ' + pipe_name)

# Extract the number of junctions impacted by low pressure conditions for each pipe closure  
number_of_junctions_impacted = dict([(k,len(v)) for k,v in junctions_impacted.items()])
        
# Plot results         
wntr.graphics.plot_network(wn, link_attribute=number_of_junctions_impacted, 
                           node_size=0, link_width=2, 
                           title='Number of junctions impacted by low pressure conditions\nfor each pipe closure')

# Plot impacted junctions for a specific pipe closure
pipe_name = '177'
wntr.graphics.plot_network(wn, node_attribute=list(junctions_impacted[pipe_name]), 
                           link_attribute=[pipe_name], node_size=20, 
                           title='Pipe ' + pipe_name + ' is critical \nfor pressure conditions at '+str(number_of_junctions_impacted[pipe_name])+' nodes')