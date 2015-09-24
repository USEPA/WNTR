import wntr
import pandas as pd
import time
import cProfile, pstats, StringIO

# Create a water network model
#inp_file = 'networks/Net6_mod_scipy.inp'
inp_file = 'networks/Net3_easy_copy.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate using Epanet
print "-----------------------------------"
print "EPANET SIMULATOR: "
pr = cProfile.Profile()
pr.enable()
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()
pr.disable()
print "-----------------------------------"
s = StringIO.StringIO()
sortby = 'cumulative'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats(20)
print s.getvalue()

s = StringIO.StringIO()
sortby = 'tottime'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats(20)
print s.getvalue()
