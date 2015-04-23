import epanetlib as en
import pandas as pd

# Create an instance of WaterNetworkModel
wn = en.network.WaterNetworkModel()

# Create an instance of ParseWaterNetwork
parser = en.network.ParseWaterNetwork()

# Populate the WaterNetworkModel with an inp file
parser.read_inp_file(wn, 'networks/Net3.inp')

# Graph the network
en.network.draw_graph(wn, title= wn.name)

# Run a hydraulic simulation with EPANET
epanet_sim = en.sim.EpanetSimulator(wn)
epanet_results = epanet_sim.run_sim()

# Plot results on the network
pressure_at_5hr = epanet_results.node.loc[(slice(None), pd.Timedelta(hours = 5)), 'pressure']
pressure_at_5hr.reset_index(level=1, drop=True, inplace=True)
attr = dict(pressure_at_5hr)
en.network.draw_graph(wn, node_attribute=attr, node_size=30, title='Pressure at 5 hours')
