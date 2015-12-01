# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Set the simulation duration to 10 hours
wn.options.duration = 3600*10

# Modifiy conditional/time controls
"""
TODO
"""

# Add a junction and pipe
wn.add_junction('new_junction', base_demand = 10, demand_pattern_name = '1', 
                elevation = 10, coordinates = (6, 25))
wn.add_pipe('new_pipe', start_node_name = 'new_junction', 
            end_node_name = '101', length = 10, diameter = 5, 
            roughness = 1, minor_loss = 3)
            
# Graph the network with new junction and pipe
wntr.network.draw_graph(wn, title= wn.name)
       
# Remove a node
#wn.remove_node('225')

# Split a pipe into two pipes separated by a junction
wn.split_pipe_with_junction('123','123A','123B','new_junction2') # split pipe 123 into two pipes named 123A and 123B, separated by a junction named new_junction

# Remove a link
#wn.remove_link('123B')

# Change junction characteristics
junction = wn.get_node('121')
junction.elevation = junction.elevation + 0.1

# Change pipe characteristics
pipe = wn.get_link('122')
pipe.diameter = pipe.diameter/2

# Change tank capacity
tank = wn.get_node('1')
tank.diameter = tank.diameter*1.1

# Change tank operations
tank = wn.get_node('3')
tank.max_level = tank.max_level*1.1

# Change pump operations, open pump 335 if tank 1 drops below 2 meters
"""
TODO
"""

# Change valve setting
"""
TODO
"""

# Change supply
reservoir = wn.get_node('River')
reservoir.base_head = reservoir.base_head*0.9 # decrease by 10%

# Change demand
junction = wn.get_node('121')
junction.base_demand = junction.base_demand*2

# Set nominal pressure to 30 meters for all nodes
for junction_name, junction in wn.junctions():
    junction.minimum_pressure = 0.0
    junction.nominal_pressure = 30.0

# Create a tank leak
tank = wn.get_node('3')     
tank.add_leak(3.14159*(0.05/2)**2)
active_control_action = wntr.network.TargetAttributeControlAction(tank, 'leak_status', True)
inactive_control_action = wntr.network.TargetAttributeControlAction(tank, 'leak_status', False)
control = wntr.network.TimeControl(wn, 4*3600, 'SIM_TIME', False, active_control_action)
wn.add_control(control)
control = wntr.network.TimeControl(wn, 8*3600, 'SIM_TIME', False, inactive_control_action)
wn.add_control(control)

# Create a junction leak
junction = wn.get_node('173')         
junction.add_leak(3.14159*(0.05/2)**2)
active_control_action = wntr.network.TargetAttributeControlAction(junction, 'leak_status', True)
inactive_control_action = wntr.network.TargetAttributeControlAction(junction, 'leak_status', False)
control = wntr.network.TimeControl(wn, 4*3600, 'SIM_TIME', False, active_control_action)
wn.add_control(control)
control = wntr.network.TimeControl(wn, 8*3600, 'SIM_TIME', False, inactive_control_action)
wn.add_control(control)

# Simulate hydraulics
#sim = wntr.sim.ScipySimulator(wn, pressure_driven = True)
#results = sim.run_sim()

# Write inp file
#wn.write_inpfile('ModifiedNet3.inp')
