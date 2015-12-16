import wntr

# Create an empty water network model
wn = wntr.network.WaterNetworkModel()

# Populate the model
wn.options.duration = 24*3600
wn.options.hydraulic_timestep = 15*60
wn.options.pattern_timestep = 60*60

wn.add_pattern('pat1', [1])
wn.add_pattern('pat2', [1,2,3,4,5,6,7,8,9,10])

wn.add_junction('node1', base_demand=0.01, demand_pattern_name='pat1', 
               elevation=100.0, coordinates=(1,2))

wn.add_junction('node2', base_demand=0.02, demand_pattern_name='pat2', 
               elevation=50.0, coordinates=(1,3))

wn.add_pipe('pipe1', 'node1', 'node2', length=304.8, diameter=0.3048, 
            roughness=100, minor_loss=0.0, status='OPEN')

wn.add_reservoir('res', base_head=125, head_pattern_name='pat1', 
                 coordinates=(0,2))
            
wn.add_pipe('pipe2', 'node1', 'res', length=100, diameter=0.3048, 
            roughness=100, minor_loss=0.0, status='OPEN')

# Simulate hydraulics
sim = wntr.sim.ScipySimulator(wn)
results = sim.run_sim()

# Draw the network
wntr.network.draw_graph(wn)