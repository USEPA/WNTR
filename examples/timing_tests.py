import wntr
import pandas as pd
import time

# Create a water network model
inp_file = 'networks/Net6_mod_scipy.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

wn.time_options['DURATION'] = 1*3600

# Simulate using Epanet
print "-----------------------------------"
print "EPANET SIMULATOR: "
t0 = time.time()
sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()
print "\tTOTAL SIM TIME: ", time.time() - t0
print "-----------------------------------"

# Simulate using Scipy
print "-----------------------------------"
print "SCIPY SIMULATOR: "
t0 = time.time()
sim = wntr.sim.ScipySimulator(wn)
results = sim.run_sim()
print "\tTOTAL SIM TIME: ", time.time() - t0
print "-----------------------------------"

# Simulate using Pyomo
print "-----------------------------------"
print "PYOMO SIMULATOR: "
t0 = time.time()
sim = wntr.sim.PyomoSimulator(wn)
results = sim.run_sim()
print "\tTOTAL SIM TIME: ", time.time() - t0
print "-----------------------------------"
