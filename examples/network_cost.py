import wntr

# Create a water network model
inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

network_cost = wntr.metrics.cost(wn)
print "Network cost: $" + str(round(network_cost,2))

network_ghg = wntr.metrics.ghg_emissions(wn)
print "Network GHG emissions: " + str(round(network_ghg,2))
