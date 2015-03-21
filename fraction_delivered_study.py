"""
TODO This file needs to be updated to use the WaterNetworkModel 
Pyomo and Scipy only?
"""

# This script is intended to replicate the resilience study in
# Ostfeld et al (2002) Reliability simulation of water distribution systems 
# - single and multiquality, Urban Water, 4, 53-61
# NOT COMPLETE

import epanetlib as en
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units

# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
    
plt.close('all')
np.random.seed(67823)

network_inp_file = 'networks/Net1.inp'

Imax = 1000
# probability of system failure, uniform distriubtion
failure_probability = np.random.uniform(0,1,Imax) < 0.01 # 0.01 for Base, 1.0 for SA1, SA2

# demand and concentration fluctuation, uniform distriubtion
demand_multiplier = np.random.uniform(0,0.1,Imax)
conc_multiplier = np.random.uniform(0.1,0.2,Imax)

pressure_lower_bound = 40*float(units.psi/units.waterpressure) # psi to m
demand_factor = 0.9 # 90% of requested demand
quality_upper_bound = 200*float((units.mg/units.l)/(units.kg/units.m**3)) # mg/L to kg/m3

FDD = [{}]*Imax
FDV = [{}]*Imax
FDQ = [{}]*Imax

enData = en.pyepanet.ENepanet()
enData.inpfile = network_inp_file
enData.ENopen(enData.inpfile,'tmp.rpt')
    
# Create MultiDiGraph
G = en.network.epanet_to_MultiDiGraph(enData)

junction_index = [enData.ENgetnodeindex(k) for k,v in nx.get_node_attributes(G,'nodetype').iteritems() if v == en.pyepanet.EN_JUNCTION]
reservoir_index = [enData.ENgetnodeindex(k) for k,v in nx.get_node_attributes(G,'nodetype').iteritems() if v == en.pyepanet.EN_RESERVOIR]
tank_index = [enData.ENgetnodeindex(k) for k,v in nx.get_node_attributes(G,'nodetype').iteritems() if v == en.pyepanet.EN_TANK]
pump_index = [enData.ENgetnodeindex(k) for k,v in nx.get_node_attributes(G,'nodetype').iteritems() if v == en.pyepanet.EN_PUMP]    
pipe_index = [enData.ENgetlinkindex(k[2]) for k,v in en.network.get_edge_attributes_MG(G, 'linktype').iteritems() if v == en.pyepanet.EN_PIPE]    
    
for i in range(Imax):
      
    # Update demand pattern 
    for index in junction_index:
        D = enData.ENgetnodevalue(index, en.pyepanet.EN_BASEDEMAND)
        enData.ENsetnodevalue(index, en.pyepanet.EN_BASEDEMAND, D*demand_multiplier[i])
    
    # Update initial quality at source and tank
    for index in reservoir_index:
        enData.ENsetnodevalue(index, en.pyepanet.EN_INITQUAL, 300*conc_multiplier[i])
    for index in tank_index:
        enData.ENsetnodevalue(index, en.pyepanet.EN_INITQUAL, 1*conc_multiplier[i])
    
    if failure_probability[i]:
        component_failure = np.random.uniform(0,1,1)
        time_of_outage = np.random.uniform(0,24,1) 
        duration_of_repair = np.random.uniform(0,8,1)

        # pump failure
        if component_failure < 0.6:
            pump_to_fail = np.random.choice(pump_index)
            print "pump failure"
            print "   pump = ", pump_to_fail, " time = ", str(time_of_outage[0]), " duration = ", str(duration_of_repair[0])
            #enData.ENsetnodevalue(pump_to_fail, en.pyepanet.EN_SETTING, 0) # ???
            # NOT COMPLETE
            
        # pipe failure
        if component_failure >= 0.6 and component_failure < 0.9:
            pipe_to_fail = np.random.choice(pipe_index)
            print "pipe failure"
            print "   pipe = ", pipe_to_fail, " time = ", str(time_of_outage[0]), " duration = ", str(duration_of_repair[0])
            #enData.ENsetlinkvalue(pipe_to_fail, en.pyepanet.EN_SETTING, 0) # ???
            # NOT COMPLETE
            
        # source failure
        if component_failure >= 0.9:
            source_to_fail = np.random.choice(reservoir_index)
            print "source failure"
            print "   source = ", source_to_fail, " time = ", str(time_of_outage[0]), " duration = ", str(duration_of_repair[0])
            #enData.ENsetnodevalue(source_to_fail, en.pyepanet.EN_INITQUAL, 0) ???
            # NOT COMPLETE

    # update G            
    G = en.network.epanet_to_MultiDiGraph(enData)
    
    # Run hydarulic and WQ simulation and save data
    G = en.sim.eps_hydraulic(enData, G)
    G = en.sim.eps_waterqual(enData, G)
    
     # Calculate metrics                    
    FDD[i] = en.metrics.fraction_delivered_demand(G,pressure_lower_bound,demand_factor)
    FDV[i] = en.metrics.fraction_delivered_volume(G,pressure_lower_bound)    
    FDQ[i] = en.metrics.fraction_delivered_quality(G,quality_upper_bound)
    
    # close and reopen inpfile
    enData.ENclose()
    enData.ENopen(enData.inpfile,'tmp.rpt')
    
    