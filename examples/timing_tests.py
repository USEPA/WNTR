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
epa_sim = wntr.sim.EpanetSimulator(wn)
t1 = time.time()
results = epa_sim.run_sim()
t2 = time.time()
total_epanet_time = t2 - t0
epanet_obj_creation_time = t1-t0
epanet_run_sim_time = t2-t1
print "-----------------------------------"

# Simulate using Scipy
print "-----------------------------------"
print "SCIPY SIMULATOR: "
t0 = time.time()
sci_sim = wntr.sim.ScipySimulator(wn)
t1 = time.time()
results = sci_sim.run_sim()
t2 = time.time()
total_scipy_time = t2 - t0
scipy_obj_creation_time = t1-t0
scipy_run_sim_time = t2-t1
print "-----------------------------------"

# Simulate using Pyomo
print "-----------------------------------"
print "PYOMO SIMULATOR: "
t0 = time.time()
pyo_sim = wntr.sim.PyomoSimulator(wn)
t1 = time.time()
results = pyo_sim.run_sim()
t2 = time.time()
total_pyomo_time = t2 - t0
pyomo_obj_creation_time = t1-t0
pyomo_run_sim_time = t2-t1
print "-----------------------------------"


print('{0:<30s}{1:<12s}{2:<12s}{3:<12s}'.format('Category','Epanet','Scipy','Pyomo'))
print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('Total Sim Time',total_epanet_time,total_scipy_time, total_pyomo_time))
print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('Sim obj creation time',epanet_obj_creation_time,scipy_obj_creation_time, pyomo_obj_creation_time))
print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('run_sim time',epanet_run_sim_time,scipy_run_sim_time, pyomo_run_sim_time))
print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('Prep time before main loop',epa_sim.prep_time_before_main_loop, sci_sim.prep_time_before_main_loop, pyo_sim.prep_time_before_main_loop))
print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('Total solve time',sum(epa_sim.solve_step[i] for i in epa_sim.solve_step.keys()),sum(sci_sim.solve_step[i] for i in sci_sim.solve_step.keys()), sum(pyo_sim.solve_step[i] for i in pyo_sim.solve_step.keys())))
print('{0:<30s}{1:<12.4s}{2:<12.4s}{3:<12.4f}'.format('Build pyomo model time','n/a','n/a', sum(pyo_sim.build_model_time[i] for i in pyo_sim.build_model_time.keys())))
wn_nodes = [name for name, node in wn.nodes()]
for i in xrange(len(results.node.loc[wn_nodes[0]].index)):
    print('{0:<30s}{1:<12.4f}{2:<12.4f}{3:<12.4f}'.format('Solve time t='+str(i),epa_sim.solve_step[i],sci_sim.solve_step[i], pyo_sim.solve_step[i]))





print 'Solve time refers to:'
print 'opt.solve for pyomo'
print 'newton solve for scipy'
print 'ENrunH for epanet'
