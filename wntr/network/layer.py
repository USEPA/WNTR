"""
The wntr.network.layer module includes methods to generate network layers
(information that is not stored in the water network model or the graph).
"""
import numpy as np
import pandas as pd
import random
import math
from wntr.network.controls import ValueCondition, RelativeCondition

def generate_valve_layer(wn, placement_type='strategic', n=1, seed=None):
    """
    Generate valve layer data, which can be used in valve segmentation analysis.

    Parameters
    -----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object
        
    placement_type : string
        Options include 'strategic' and 'random'.  
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve. In this case, n is generally 0, 1 or 2 
          (i.e. N, N-1, N-2 valve placement).
        - If 'random', then n randomly placed valves are used to define the 
          valve layer.
        
    n : int
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve.
        - If 'random', n is the number of number of randomly placed valves.
        
    seed : int or None
        Random seed
       
    Returns
    ---------
    valve_layer : pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    """
    
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    valve_layer = []
    if placement_type=='random':
        all_valves = []
        for pipe_name, pipe in wn.pipes():
            all_valves.append((pipe_name, pipe.start_node_name))
            all_valves.append((pipe_name, pipe.end_node_name))

        for valve_tuple in random.sample(all_valves, n):
            pipe_name, node_name = valve_tuple
            valve_layer.append([pipe_name, node_name])
            
    elif placement_type == 'strategic':
        for node_name, node in wn.nodes():
            links = wn.get_links_for_node(node_name)
            for l in np.random.choice(links, max(len(links)-n,0), replace=False):
                valve_layer.append([l, node_name])
            
    valve_layer = pd.DataFrame(valve_layer, columns=['link', 'node'])  
    
    return valve_layer
    
def autogenerate_full_cps_layer(wn, placement_type='simple', timed_control_assignments='remote', edge_types='MODBUS', ownership = 'auto', n=1, s=1, verbose=0):
    """
    Generate cps layer data, which can be used to automate creation of a simple or complex network topology.
    A simple topology will assume that all data is generated at the node
    
    Parameters
    -----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object
        
    placement_type : string
        Options include 'complex' and 'simple'. Simple placements will link each end node directly to the SCADA and nothing else. This is default behavior, pending any additional behavior limited to 'simple' topography.
        Complex placement will (FOR NOW) add a connection between each CPS node and 'n' other CPS nodes representing sensor data duplication for enhanced node resiliency
    
    timed_control_assignments : string
        Options include 'remote' and 'local'. Remote assignment designates all time-based controls to SCADA control, while local assigns them to the most relevant CPS object nearby
    
    edge_types : string
        Options include 'MODBUS', 'EIP', 'SER', 'random'
        
    ownership : string 
        Options include 'auto' and 'manual'. By default, all new PLC will be assigned to and owned by SCADA-HMI, while sensors will be assigned to their corresponding PLC units. Manual will not create these assignments.
    
    n : int
        Number of sensor duplication edges for each node in 'complex' topology. 
        WIP -- currently, nodes are assigned paired PLC simply based off the physically nearest cps_node. If cps_nodes have [0,0] coordinates, node will be assigned pair at random.
    
    s : int
        Number of 
    
    verbose : int 
        Options are 0 and anything other than 0
    
    Returns
    ---------
    cps_layer : pandas DataFrame
        
    """
    
    cps_layer = []
    edges = ['MODBUS', 'EIP', 'SER']
    all_edges = []
    SCADA = "SCADA-HMI"
    HIST = "SCADA-HIST"
    wn._cps_reg.add_SCADA(SCADA)
    wn._cps_reg.add_SCADA(HIST)
    #TODO: Should SCADA-HIST be an in-network edge? Or, as it doesn't relate to SCADA operations in the physical capacity, should it be external to the CPS-layer? Maybe a third IT-only layer?
    wn._cps_edges.add_EIP(SCADA+"_EIP_"+HIST, SCADA, HIST) #use Ethernet over IP for SCADA->HIST communication until a more fitting protocol can be decided.
    if(verbose != 0):
        print("Defult Primary SCADA: " + SCADA + " added. SCADA Historian Stand-in: " + HIST + " added.")
    for control_name, control in wn.controls():
        if verbose != 0:
            print("Control being assigned: " + control.__str__())
        if isinstance(control._condition, (ValueCondition, RelativeCondition)):
            plc_check = control._condition._source_obj.__str__()+"-plc"
            if plc_check not in wn._cps_reg:
                if control._condition._source_obj._coordinates != [0,0]:
                    # autogenerate rough coordinates for PLC objects based on location of object against whom they act
                    wn._cps_reg.add_PLC(plc_check, control._condition._source_obj._coordinates) 
                else:
                    wn._cps_reg.add_PLC(plc_check) 
                # If automatic ownership set to 'auto', generate ownership to SCADA-HMI
                if ownership == 'auto':
                    wn._cps_reg[SCADA].add_owned(plc_check)
                    wn._cps_reg[plc_check].add_owner(SCADA)
                # Add complex sensor nodes here to avoid mutating registry during later iteration
                if placement_type == 'complex':
                    # Add RTU and corresponding Serial edge representing end sensor (placeholding until the potential/necessity of a sensor CPS object is considered)
                    wn._cps_reg.add_RTU("S-"+plc_check, wn._cps_reg[plc_check]._coordinates)
                    wn._cps_reg[plc_check].add_owned("S-"+plc_check)
                    wn._cps_reg["S-"+plc_check].add_owner(plc_check)
                    if verbose != 0:
                        print("RTU: S-"+plc_check+" added.")                    
                if edge_types=="MODBUS":
                    wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+plc_check, SCADA, plc_check)
                    all_edges.append((SCADA+"_MODBUS_"+plc_check, SCADA))
                    all_edges.append((SCADA+"_MODBUS_"+plc_check, plc_check))
                elif edge_types=="EIP":
                    wn._cps_edges.add_EIP(SCADA+"_EIP_"+plc_check, SCADA, plc_check)
                    all_edges.append((SCADA+"_EIP_"+plc_check, SCADA))
                    all_edges.append((SCADA+"_EIP_"+plc_check, plc_check))
                elif edge_types=="SER":
                    wn._cps_edges.add_SER(SCADA+"_SER_"+plc_check, SCADA, plc_check)
                    all_edges.append((SCADA+"_SER_"+plc_check, SCADA))
                    all_edges.append((SCADA+"_SER_"+plc_check, plc_check))
                elif edge_types=="random":
                    choice = np.random.choice(edges)
                    if choice=="MODBUS":
                        wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+plc_check, SCADA, plc_check)
                        all_edges.append((SCADA+"_MODBUS_"+plc_check, SCADA))
                        all_edges.append((SCADA+"_MODBUS_"+plc_check, plc_check))
                    elif choice=="EIP":
                        wn._cps_edges.add_EIP(SCADA+"_EIP_"+plc_check, SCADA, plc_check)
                        all_edges.append((SCADA+"_EIP_"+plc_check, SCADA))
                        all_edges.append((SCADA+"_EIP_"+plc_check, plc_check))
                    elif choice=="SER":
                        wn._cps_edges.add_SER(SCADA+"_SER_"+plc_check, SCADA, plc_check)
                        all_edges.append((SCADA+"_SER_"+plc_check, SCADA))
                        all_edges.append((SCADA+"_SER_"+plc_check, plc_check))
                else: #default to MODBUS over IP
                    wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+plc_check, SCADA, plc_check)
                    all_edges.append((SCADA+"_MODBUS_"+plc_check, SCADA))
                    all_edges.append((SCADA+"_MODBUS_"+plc_check, plc_check))
                if verbose != 0:
                    print("PLC: "+plc_check+" added.")
                control.assign_cps(plc_check)
                if verbose != 0:
                    print("Control "+control_name+" assigned to " + plc_check)
            else:
                control.assign_cps(plc_check)
                if verbose != 0:
                    print("Control "+control_name+" assigned to pre-existing PLC " + plc_check)
        else: #if not a value or relative condition, it must be a function or time-based condition. Assume time-based for now.
            for action in control.actions():
                if timed_control_assignments=='remote':
                    control.assign_cps(SCADA)
                elif timed_control_assignments=='local':   
                    target = action._target_obj.__str__()+"-plc" 
                    if target not in wn._cps_reg:
                        wn._cps_reg.add_PLC(target)
                        if ownership == 'auto':
                            wn._cps_reg[SCADA].add_owned(target)
                            wn._cps_reg[target].add_owner(SCADA)
                        if placement_type == 'complex':
                            # Add RTU and corresponding Serial edge representing end sensor (placeholding until the potential/necessity of a sensor CPS object is considered)
                            wn._cps_reg.add_RTU("S-"+target, wn._cps_reg[target]._coordinates)                      
                            if verbose != 0:
                                print("RTU: S-"+target+" added.")                                      
                        if edge_types=="MODBUS":
                            wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+target, SCADA, target)
                            all_edges.append((SCADA+"_MODBUS_"+target, SCADA))
                            all_edges.append((SCADA+"_MODBUS_"+target, target))
                        elif edge_types=="EIP":
                            wn._cps_edges.add_EIP(SCADA+"_EIP_"+target, SCADA, target)
                            all_edges.append((SCADA+"_EIP_"+target, SCADA))
                            all_edges.append((SCADA+"_EIP_"+target, target))
                        elif edge_types=="SER":
                            wn._cps_edges.add_SER(SCADA+"_SER_"+target, SCADA, target)
                            all_edges.append((SCADA+"_SER_"+target, SCADA))
                            all_edges.append((SCADA+"_SER_"+target, target))
                        elif edge_types=="random":
                            choice = np.random.choice(edges)
                            if choice=="MODBUS":
                                wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+target, SCADA, target)                        
                                all_edges.append((SCADA+"_MODBUS_"+target, SCADA))
                                all_edges.append((SCADA+"_MODBUS_"+target, target))
                            elif choice=="EIP":
                                wn._cps_edges.add_EIP(SCADA+"_EIP_"+target, SCADA, target)
                                all_edges.append((SCADA+"_EIP_"+target, SCADA))
                                all_edges.append((SCADA+"_EIP_"+target, target))
                            elif choice=="SER":
                                wn._cps_edges.add_SER(SCADA+"_SER_"+target, SCADA, target)
                                all_edges.append((SCADA+"_SER_"+target, SCADA))
                                all_edges.append((SCADA+"_SER_"+target, target))
                        else: #default to MODBUS over IP
                            wn._cps_edges.add_MODBUS(SCADA+"_MODBUS_"+target, SCADA, target)
                            all_edges.append((SCADA+"_MODBUS_"+target, SCADA))
                            all_edges.append((SCADA+"_MODBUS_"+target, target))
                        if verbose != 0:
                            print("PLC: "+target+" added.")
                    control.assign_cps(target)
                    if verbose != 0:
                        print("Control "+control_name+" assigned to " + target)
                    
                else:
                    print("No valid timed control location preference provided, defaulting to SCADA-controlled (remote).")
                    control.assign_cps(SCADA)
               
    if placement_type == 'complex':
        # Add PLC-PLC check pairs/tuples based on N, sensor duplication based on S
        node_list = wn.cps_nodes()
        # TODO: a quick distance chart to reduce the nested loops here which make the algorithmic complexity gods sad
        #dist = np.zeros(wn.cps_nodes().__len__(),wn.cps_nodes().__len__())
            
        for node_name, node in wn.cps_nodes():
            # repeat for the desired number of duplicate edges
            for i in range(n):
                if node._coordinates != [0,0]:
                    #print(node._coordinates)
                    shortest_dist = 999
                    closest_node = None
                    for node2_name, node2 in wn.cps_nodes(): 
                        if(node2_name != node_name):
                            if(closest_node != None):
                                if (closest_node._name+"_MODBUS_"+node_name not in wn._cps_edges) and (node2_name+"_MODBUS_"+node_name not in wn._cps_edges): #don't add duplicate edges
                                    dist = math.dist(node._coordinates, node2._coordinates)
                                    if dist < shortest_dist:
                                        shortest_dist = dist
                                        closest_node = node2
                            elif (node2_name+"_MODBUS_"+node_name not in wn._cps_edges): #again, duplicate protection
                                dist = math.dist(node._coordinates, node2._coordinates)
                                shortest_dist = dist
                                closest_node = node2
                    if (closest_node._name+"_MODBUS_"+node_name not in wn._cps_edges):
                        wn._cps_edges.add_MODBUS(closest_node._name+"_MODBUS_"+node_name, closest_node._name, node_name)            
                        all_edges.append((closest_node._name+"_MODBUS_"+node_name, closest_node._name))
                        all_edges.append((closest_node._name+"_MODBUS_"+node_name, node_name))
                    #print("Complexity edge: " + closest_node._name+"_MODBUS_"+node_name +" added.")
            #adding SER edge if complex, and Sensor RTU has been added during previous autogeneration
            if("S-"+node_name in wn._cps_reg):
                wn._cps_edges.add_SER(node_name+"_SER_S-"+node_name, node_name, "S-"+node_name) 
                #print("Edge: " + node_name+"_SER_S-"+node_name+" added")
                all_edges.append((node_name+"_SER_S-"+node_name, node_name))
                all_edges.append((node_name+"_SER_S-"+node_name, "S-"+node_name))
                for i in range(s):
                    if wn._cps_reg["S-"+node_name]._coordinates != [0,0]:
                        #print(node._coordinates)
                        shortest_dist = 999
                        closest_node = None
                        for node2_name, node2 in wn.cps_nodes(): 
                            if(node2_name != node_name) and not (node2_name.startswith("S-")): #ignore other sensor nodes
                                if(closest_node != None):
                                    if (closest_node._name+"_SER_S-"+node_name not in wn._cps_edges) and (node2_name+"_SER_S-"+node_name not in wn._cps_edges): #don't add duplicate edges
                                        dist = math.dist(node._coordinates, node2._coordinates)
                                        if dist < shortest_dist:
                                            shortest_dist = dist
                                            closest_node = node2
                                elif (node2_name+"_SER_S-"+node_name not in wn._cps_edges): #again, duplicate protection
                                    dist = math.dist(node._coordinates, node2._coordinates)
                                    shortest_dist = dist
                                    closest_node = node2
                        if (closest_node._name+"_SER_S-"+node_name not in wn._cps_edges):
                            #print("Edge: " + closest_node._name+"_SER_S-"+node_name + " adding")
                            wn._cps_edges.add_SER(closest_node._name+"_SER_S-"+node_name, closest_node._name, "S-"+node_name)            
                            all_edges.append((closest_node._name+"_SER_S-"+node_name, closest_node._name))
                            all_edges.append((closest_node._name+"_SER_S-"+node_name, "S-"+node_name))
                        #print("Complexity edge: " + closest_node._name+"_SER_"+node_name +" added.")
                            
    for edge_tuple in all_edges:
        edge_name, cps_node_name = edge_tuple
        cps_layer.append([edge_name, cps_node_name])          
            
    cps_layer = pd.DataFrame(cps_layer, columns=['edge', 'cps_node'])  
    
    return cps_layer