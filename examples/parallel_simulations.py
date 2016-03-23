import wntr
import numpy as np
from multiprocessing import Pool
import time
import pickle
import logging

def run_scenario(pipe_to_break):
    f = open('wn.pickle', 'r')
    wn = pickle.load(f)
    f.close()
    wn.split_pipe_with_junction(pipe_to_break, pipe_to_break+'__A', pipe_to_break+'__B', 'leak_'+pipe_to_break)
    leak = wn.get_node('leak_'+pipe_to_break)
    leak.add_leak(wn, 0.01, 0.75, 3600, 5*3600)
    sim = wntr.sim.WNTRSimulator(wn, pressure_driven=True)
    results = sim.run_sim()
    return results

np.random.seed(0)

inp_file = 'networks/Net3.inp'
wn = wntr.network.WaterNetworkModel(inp_file)
wn.options.duration = 72*3600
wn.options.hydraulic_timestep = 3600
pipes_to_break = list(np.random.choice(wn.pipe_name_list(), size=10, replace=False))
f=open('wn.pickle','w')
pickle.dump(wn,f)
f.close()

# run in serial
t0 = time.time()
results_list_serial = []
for pipe_name in pipes_to_break:
    results_list_serial.append(run_scenario(pipe_name))
t1 = time.time()
print 'serial time: ',t1-t0

# run in parallel
t2 = time.time()
p = Pool(5) # number of processors to use
results_list = p.map(run_scenario, pipes_to_break)
t3 = time.time()
print 'parallel time: ',t3-t2

# make sure the results are the same
for i, serial_result in enumerate(results_list_serial):
    parallel_result = results_list[i]
    assert ((serial_result.node==parallel_result.node).all().all().all())
    assert ((serial_result.link==parallel_result.link).all().all().all())
