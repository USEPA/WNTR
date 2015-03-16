import epanetlib as en

# Create an instance of WaterNetworkModel
wn = en.network.WaterNetworkModel()

# Create an instance of ParseWaterNetwork
parser = en.network.ParseWaterNetwork()

# Populate the WaterNetworkModel with an inp file
parser.read_inp_file(wn, 'networks/Net3.inp')

# Graph the network
en.network.draw_graph(wn, title= wn.name)
