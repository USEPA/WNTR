import wntr.stormwater as wntr

inp_file = 'networks/Example.inp'

# Conduit criticality analysis
conduits = ['C5'] #, 'C8', 'C11']
results = {}
for conduit in conduits:
    print(conduit)
    swn = wntr.network.StormWaterNetworkModel(inp_file)
    
    swn.links.loc[conduit,"MaxFlow"] = 0.0000001
    
    sim = wntr.sim.SWMMSimulator(swn)
    results[conduit] = sim.run_sim(conduit)

# Post process results
for conduit in conduits:
    flowrate = results[conduit].link['FLOW_VELOCITY'].mean()
    wntr.graphics.plot_network(swn, link_attribute=flowrate, 
                               link_width=2, link_range=[0,1])
