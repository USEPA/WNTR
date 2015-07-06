import epanetlib as en
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units
import time
import pickle 

# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa

plt.close('all')

inp_file = 'networks/Net6_mod.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

nHours = 23
wn.time_options['DURATION'] = nHours*3600
wn.time_options['HYDRAULIC TIMESTEP'] = 3600

# Run a demand driven simulation and store results
#pyomo_sim_dd = en.sim.PyomoSimulator(wn,'DEMAND DRIVEN')
#print '\nRunning Demand Driven Simulation'
#res_demand_driven = pyomo_sim_dd.run_sim()
#pickle.dump(res_demand_driven, open('DD_results_net6.pickle', 'wb'))
res_demand_driven = pickle.load(open('DD_results_net6.pickle', 'rb'))

# Run a pressure driven simulation with varying nominal pressures
wn.set_nominal_pressures(res = res_demand_driven)

# Net 6 has 61 pumps, at 22 unique locations
pump_stations = {
    '1': ['PUMP-3829'], # Controls TANK-3326
    '2': ['PUMP-3830', 'PUMP-3831', 'PUMP-3832', 'PUMP-3833', 'PUMP-3834'], #  Controls TANK-3325, Pump station 2 is connected to the reservoir
    '3': ['PUMP-3835', 'PUMP-3836', 'PUMP-3837', 'PUMP-3838'], #, # Controls TANK-3333
    '4': ['PUMP-3839', 'PUMP-3840', 'PUMP-3841'], # Controls TANK-3333
    '5': ['PUMP-3842', 'PUMP-3843', 'PUMP-3844'], # Controls TANK-3335
    '6': ['PUMP-3845', 'PUMP-3846'], # Controls TANK-3336
    '7': ['PUMP-3847', 'PUMP-3848'], # Controls TANK-3337
    '8': ['PUMP-3849', 'PUMP-3850', 'PUMP-3851', 'PUMP-3852', 'PUMP-3853'],#, # Controls TANK-3337
    '9': ['PUMP-3854', 'PUMP-3855', 'PUMP-3856'], # TANK-3340
    '10': ['PUMP-3857', 'PUMP-3858', 'PUMP-3859'], # Controls TANK-3341
    '11': ['PUMP-3860', 'PUMP-3861', 'PUMP-3862'], #, # Controls TANK-3342
    '12': ['PUMP-3863', 'PUMP-3864', 'PUMP-3865', 'PUMP-3866'], # Controls TANK-3343
    '13': ['PUMP-3867', 'PUMP-3868', 'PUMP-3869'], # Controls TANK-3346
    '14': ['PUMP-3870', 'PUMP-3871'], # Controls TANK-3347
    '15': ['PUMP-3872', 'PUMP-3873', 'PUMP-3874'], # Controls TANK-3349
    '16': ['PUMP-3875', 'PUMP-3876', 'PUMP-3877'], # Controls TANK-3348
    '17': ['PUMP-3878'],#, # Controls TANK-3352
    '18': ['PUMP-3879', 'PUMP-3880', 'PUMP-3881'], # Controls TANK-3353
    '19': ['PUMP-3882', 'PUMP-3883', 'PUMP-3884'], #, # Controls TANK-3355
    '20': ['PUMP-3885'], # Controls TANK-3354
    '21': ['PUMP-3886', 'PUMP-3887', 'PUMP-3888'], # Controls TANK-3356
    '22': ['PUMP-3889'], # No curve, only power 15?
    'ALL': [],
    'None': []}

start_time = '0 days 02:00:00'
end_time = '0 days 17:00:00'

# Power outage scenarios
pyomo_results = {}
for k,v in pump_stations.iteritems():

    print ">>>>>>>>>>>>>>>>>>>>>>>"
    print "Scenario: ", k
    print ">>>>>>>>>>>>>>>>>>>>>>>"

    t0 = time.time()
    # Copy the water network and create a sim object
    wn_power = wn.copy()

    pyomo_sim = en.sim.PyomoSimulator(wn_power, 'PRESSURE DRIVEN')
    
    # Add power outage    
    if k is 'ALL':
        pyomo_sim.all_pump_outage(start_time, end_time)
    if k is 'None':
        pass
    else:
        for pump_name in v:
            pyomo_sim.add_pump_outage(pump_name, start_time, end_time)
            
    # Re-simulate
    pyomo_results[k] = pyomo_sim.run_sim()
    
    t1 = time.time() - t0
    print t1
    
pickle.dump(pyomo_results, open('all_scenario_results_15hr.pickle', 'wb'))
