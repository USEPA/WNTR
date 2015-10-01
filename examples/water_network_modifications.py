# Modify Network Stucture/Operations/Controls and simulate hydraulics
import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Set the simulation duration to 10 hours
wn.options.duration = 3600*10

# Add a junction and pipe
wn.add_junction('new junction', base_demand = 10, demand_pattern_name = '1', 
                elevation = 10, coordinates = (6, 25))
wn.add_pipe('new pipe', start_node_name = 'new junction', 
            end_node_name = '101', length = 10, diameter = 5, 
            roughness = 1, minor_loss = 3)
            
# Graph the network with new junction and pipe
wntr.network.draw_graph(wn, title= wn.name)
       
# Remove a node and pipe


# Change junction characteristics
junction = wn.get_node('121')
junction.elevation = junction.elevation + 0.1

# Change pipe characteristics
pipe = wn.get_link('123')
pipe.diameter = pipe.diameter/2

# Change tank capacity
tank = wn.get_node('1')
tank.diameter = tank.diameter*1.1

# Change tank operations
tank = wn.get_node('3')
tank.max_level = tank.max_level*1.1

# Change pump operations, open pump 335 if tank 1 drops below 2 meters
wn.add_conditional_controls('335','1',2.0,'OPEN','ABOVE') 

# Change valve setting


# Change supply
reservoir = wn.get_node('River')
reservoir.base_head = reservoir.base_head*0.9 # decrease by 10%

# Change demand
junction = wn.get_node('121')
junction.base_demand = junction.base_demand*2

# Set nominal pressure to 30 meters for all nodes
wn.set_nominal_pressures(constant_nominal_pressure = 30.0, 
                         minimum_pressure = 0) 

# Simulate hydraulics
sim = wntr.sim.PyomoSimulator(wn,'PRESSURE DRIVEN')
results = sim.run_sim()
