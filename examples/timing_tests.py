import wntr
import pandas as pd
import time

# Create a water network model
#inp_file = 'networks/Net6_mod_scipy.inp'
inp_file = 'networks/Net3_timing.inp'
wn = wntr.network.WaterNetworkModel(inp_file)

# Simulate using Epanet
print "-----------------------------------"
print "EPANET SIMULATOR: "
t0 = time.time()
sim = wntr.sim.EpanetSimulator(wn)
t1 = time.time()
results = sim.run_sim()
t2 = time.time()
total_epanet_time = t2 - t0
epanet_obj_creation_time = t1-t0
epanet_run_sim_time = t2-t1
print "-----------------------------------"

# Simulate using Scipy
print "-----------------------------------"
print "SCIPY SIMULATOR: "
t0 = time.time()
sim = wntr.sim.ScipySimulator(wn)
t1 = time.time()
results = sim.run_sim()
t2 = time.time()
total_scipy_time = t2 - t0
scipy_obj_creation_time = t1-t0
scipy_run_sim_time = t2-t1
print "-----------------------------------"

# Simulate using Pyomo
print "-----------------------------------"
print "PYOMO SIMULATOR: "
t0 = time.time()
sim = wntr.sim.PyomoSimulator(wn)
t1 = time.time()
results = sim.run_sim()
t2 = time.time()
total_pyomo_time = t2 - t0
pyomo_obj_creation_time = t1-t0
pyomo_run_sim_time = t2-t1
print "-----------------------------------"

print('{0:>20s}{1:>20s}{2:>20s}{3:>20s}'.format('Category','Epanet','Scipy','Pyomo'))
print('{0:>20s}{1:>20.4f}{2:>20.4f}{3:>20.4f}'.format('Total Sim Time',total_epanet_time,total_scipy_time, total_pyomo_time))
print('{0:>20s}{1:>20.4f}{2:>20.4f}{3:>20.4f}'.format('Obj creation time',epanet_obj_creation_time,scipy_obj_creation_time, pyomo_obj_creation_time))
