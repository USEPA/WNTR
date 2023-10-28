# Conduit criticality analysis
import matplotlib.pylab as plt
import wntr.stormwater as swntr

inp_file = 'networks/Example.inp'
swn = swntr.network.StormWaterNetworkModel(inp_file)

results = {}
fig, ax = plt.subplots()

for conduit_name in swn.conduit_name_list:
    print(conduit_name)
    swn = swntr.network.StormWaterNetworkModel(inp_file)
    swn.conduits.loc[conduit_name, "MaxFlow"] = 0.0000001
    sim = swntr.sim.SWMMSimulator(swn)
    results[conduit_name] = sim.run_sim(conduit_name)

    flowrate = results[conduit_name].link['FLOW_VELOCITY']
    #swntr.graphics.plot_network(swn, 
    #                            link_attribute=flowrate.mean(axis=0), 
    #                            link_width=2, 
    #                            link_range=[0,1])
    flowrate.mean(axis=1).plot(ax=ax)
    
print(results['C1'].node.keys())
