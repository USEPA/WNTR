import wntr

# Generate a water network model
wn = wntr.network.WaterNetworkModel()
wn.add_pattern('pat1', [1])
wn.add_pattern('pat2', [1,2,3,4,5,6,7,8,9,10])
wn.add_junction('node1', base_demand=0.01, demand_pattern_name='pat1', 
	elevation=100.0, coordinates=(1,2))
wn.add_junction('node2', base_demand=0.02, demand_pattern_name='pat2', 
	elevation=50.0, coordinates=(1,3))
wn.add_pipe('pipe1', 'node1', 'node2', length=304.8, diameter=0.3048, roughness=100, 
	minor_loss=0.0, status='OPEN')
wn.add_reservoir('res', base_head=125, head_pattern_name='pat1', coordinates=(0,2))
wn.add_pipe('pipe2', 'node1', 'res', length=100, diameter=0.3048, roughness=100, 
	minor_loss=0.0, status='OPEN')
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 15*60
wn.options.pattern_timestep = 60*60

# Simulate hydraulics
sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

# Save the water network to an inp file
wn.write_inpfile('filename.inp')

# Generate another water network model from an inp file
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Modify the network model
wn.options.duration = 3600*10

# Add a junction and pipe
wn.add_junction('new_junction', base_demand = 10, demand_pattern_name = '1', 
                elevation = 10, coordinates = (6, 25))
wn.add_pipe('new_pipe', start_node_name = 'new_junction', 
            end_node_name = '101', length = 10, diameter = 5, 
            roughness = 1, minor_loss = 3)
            
# Graph the network with new junction and pipe
wntr.network.draw_graph(wn, title= wn.name)
 
# Remove a link
wn.remove_link('153')

# Change junction characteristics
junction = wn.get_node('121')
junction.elevation = junction.elevation + 0.1

# Change pipe characteristics
pipe = wn.get_link('122')
pipe.diameter = pipe.diameter*0.5

# Change tank capacity
tank = wn.get_node('1')
tank.diameter = tank.diameter*1.1

# Change tank operations
tank = wn.get_node('3')
tank.max_level = tank.max_level*1.1

# Change supply
reservoir = wn.get_node('River')
reservoir.base_head = reservoir.base_head*0.9 # decrease by 10%

# Change demand
junction = wn.get_node('121')
junction.base_demand = junction.base_demand*1.15

# Set nominal pressure to 15 meters for all nodes
for junction_name, junction in wn.junctions():
    junction.minimum_pressure = 0.0
    junction.nominal_pressure = 15.0

# Create a junction leak
junction = wn.get_node('173')         
junction.add_leak(wn, area=3.14159*(0.001/2)**2, start_time=4*3600, end_time=8*3600)

# Simulate hydraulics
sim = wntr.sim.WNTRSimulator(wn, pressure_driven = True)
results = sim.run_sim(solver_options={'MAXITER':300,'BACKTRACKING':True})

# Write inp file
wn.write_inpfile('ModifiedNet3.inp')
