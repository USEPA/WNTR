# Conduit criticality analysis
import matplotlib.pylab as plt
import wntr.stormwater as swntr

inp_file = 'networks/Site_Drainage_Model.inp'
swn = swntr.network.StormWaterNetworkModel(inp_file)

results = {}
fig, ax = plt.subplots()

for conduit_name in swn.conduit_name_list:
    print(conduit_name)
    swn = swntr.network.StormWaterNetworkModel(inp_file)
    swn.conduits.loc[conduit_name, "MaxFlow"] = 0.00001
    sim = swntr.sim.SWMMSimulator(swn)
    results[conduit_name] = sim.run_sim(conduit_name)

    flowrate = results[conduit_name].link['FLOW_VELOCITY']
    flowrate.mean(axis=1).plot(ax=ax, label=conduit_name)
    
plt.legend()
