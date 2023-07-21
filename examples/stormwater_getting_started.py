import wntr.stormwater as wntr
import swmmio
import pyswmm
import time

inp_file = 'networks/Example.inp'

# using swmmio and pyswmm directly
tic = time.time()
model = swmmio.Model(inp_file)

G = model.network # contains coordinates and attributes 

model.links.dataframe
model.links.geodataframe

swmmio.graphics.swmm_graphics.draw_model(model)

model.inp.save('Updated_model.inp')

sim = pyswmm.Simulation('Updated_model.inp')
sim.execute()
sim.close()

print("Run time swmmio pyswmm", time.time() - tic)
print()

results1 = wntr.io.read_outfile('Updated_model.out')

print("Run time with results object", time.time() - tic)
print()

# using WNTR wrapper
tic = time.time()
swn = wntr.network.StormWaterNetworkModel(inp_file)

G = swn.to_graph()

swn._swmmio_model.links.dataframe
swn._swmmio_model.links.geodataframe

wntr.graphics.plot_network(swn)

sim = wntr.sim.SWMMSimulator(swn)
results2 = sim.run_sim()

print("Run time WNTR wrapper", time.time() - tic)

flowrate1 = results1.link['FLOW_VELOCITY'].loc['2007-01-01 00:01:00',:]
flowrate2 = results2.link['FLOW_VELOCITY'].loc['2007-01-01 00:01:00',:]

wntr.graphics.plot_network(swn, link_attribute=flowrate1)
wntr.graphics.plot_network(swn, link_attribute=flowrate2)
