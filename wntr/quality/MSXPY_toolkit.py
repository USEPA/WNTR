# # -*- coding: utf-8 -*-
# """
# Created on Fri Jun 18 10:52:45 2021

# @author: Matthew
# """

# import numpy as np
# import epanet_toolkit as epa
# import msx_toolkit as msx
# import pandas as pd
# import os
# from sklearn.cluster import KMeans
# from sklearn.metrics import silhouette_score
# import wntr
# from scipy.linalg import cholesky
# from SALib.analyze import morris as morris_a

# def MSXRunQual(species='all', nodes='all', links='all',by_species='yes',bin_read='no',t_start=-1):
#     #Function to run a MSX model and extract timeseries of specified species, links, and nodes
#     #Inputs are a list of the desired species, nodes, links, and whether the results
#     #should be organized by species, or by model element (links and nodes)
#     #if no nodes or links are desired, then an empty list [] should be used
#     #The t_start option is a number in days which says when the results from the
#     #simulation should start to be recorded. This is helpful if a model needs to run
#     #to reach hydraulic equilbriums and the first X number of days of the simulation
#     #are not needed for the results
    
#     #The bin_read option allows for the model to be run all at once and 
#     #then the binary file is read. The reporting timesteps are based on the 
#     #reporting timestep from the inp file. If not, the results
#     #are read at each timestep from the msx model run.
        
#     if bin_read=='no':
    
#         #Extract the indicies and names for the species of interest
#         if (species=='all'):
#             species_names=[]
#             #Get the number of species 3 for species
#             species_num=msx.MSXgetcount(3)
#             #Get a list for the species id's
#             for i in range(species_num):
#                 species_names.append(msx.MSXgetID(3,i+1))
#             #get an array for the species indicies
#             species_ind=np.linspace(1,species_num,species_num)
            
#         #If there is a user supplied list of species to be extracted
#         else:
#             #Make the user-input list the variable species_names
#             species_names=species
#             #Extract the indicies for the species being specified
#             species_ind=[]
#             for i in range(len(species_names)):
#                 species_ind.append(msx.MSXgetindex(3,species_names[i]))
        
#         #Extract the node indicies for the specified nodes
#         if (nodes=='all'):
#             node_names=[]
#             #Get the number of nodes- 0 for nodes
#             node_num=epa.ENgetcount(0)
#             #Get a list for the node id's
#             for i in range(node_num):
#                 node_names.append(epa.ENgetnodeid(i+1))
#             #Get an array for the node indicies
#             node_ind=np.linspace(1,node_num,node_num)
            
#         #If there are actual nodes specified to be extracted
#         else:
#             #Make the user-input list the variable node_names
#             node_names=nodes
#             #Extract the indicies for the nodes being specified
#             node_ind=[]
#             for i in range(len(node_names)):
#                 node_ind.append(epa.ENgetnodeindex(node_names[i]))
                
#         #Do the same but for links
        
#         #Extract the link indicies for the specified nodes
#         if (links=='all'):
#             link_names=[]
#             #Get the number of links- 2 for links
#             link_num=epa.ENgetcount(2)
#             #Get a list for the link id's
#             for i in range(link_num):
#                 link_names.append(epa.ENgetlinkid(i+1))
#             #Get an array for the node indicies
#             link_ind=np.linspace(1,link_num,link_num)
            
#         #If there are actual nodes specified to be extracted
#         else:
#             #Make the user-input list the variable node_names
#             link_names=links
#             #Extract the indicies for the nodes being specified
#             link_ind=[]
#             for i in range(len(link_names)):
#                 link_ind.append(epa.ENgetlinkindex(link_names[i]))
            
        
        
#         #Create array to extract the time of the simulation steps
#         T=[]
        
#         #Initialize MSX for first timestep
#         msx.MSXinit(0)
        
#         #Initialize time left
#         t_left=1
        
#         #Create overall results dictionary
#         results={}
        
#         #If organized by species
#         if (by_species=='yes'):
#             #Create a new dictionary for each species and then within each species
#             #make a node and link list
#             for i in range(len(species_names)):
#                 results[species_names[i]]={}
#                 results[species_names[i]]['node']=[]
#                 results[species_names[i]]['link']=[]
        
#         #If organized by element
#         if (by_species=='no'):
#             #Create node key and another dictionary
#             results['node']={}
#             #Create link key and another dictionary
#             results['link']={}
            
#             #Within each dictionary make a list to be populated later during model run
#             #nodes
#             for i in range(len(node_names)):
#                 results['node'][node_names[i]]=[] 
#             #links
#             for i in range(len(link_names)):
#                 results['link'][link_names[i]]=[] 
        
        
#         #Change the input of t_start from days to seconds
#         t_start=t_start*24*60*60
        
        
#         #Create loop to run model
#         while (t_left>0):
#             #Solve the quality for that timestep
#             [t,t_left]=msx.MSXstep()
           
#             #If the results should be extracted based on t_start aka the simulation
#             #time has passed the time when we care about the results
#             if t>t_start: 
                
#                 #Append time for that step to the overall time list
#                 T.append(t)
                
#                 #If the results are to be extracted by model element
#                 if (by_species=='no'):
#                     #Extract the results from each node into a different list
#                     for j in range(len(node_names)):
#                         #Create a row for the overall results list
#                         Q_row=[]
#                         #Extract the results for each desired species at that node
#                         for i in range(len(species_names)):
#                             #0 for node    #node_ind and the species_ind
#                             Q_row.append(msx.MSXgetqual(0,int(node_ind[j]),int(species_ind[i])))
#                         results['node'][node_names[j]].append(Q_row)
                        
#                     #Extract the results from each link into a different list
#                     for j in range(len(link_names)):
#                         #Create a row for the overall results list
#                         Q_row=[]
#                         #Extract the results for each desired species at that node
#                         for i in range(len(species_names)):
#                             #0 for link    #node_ind and the species_ind
#                             Q_row.append(msx.MSXgetqual(1,int(link_ind[j]),int(species_ind[i])))
#                         results['link'][link_names[j]].append(Q_row)
                        
#                 #If the results are to be extracted by species
#                 if (by_species=='yes'):
#                     for i in range(len(species_names)):
#                         #First extract the nodes and then the links
#                         #Create empty lists for each row to be added
#                         Q_row_node=[]
#                         Q_row_link=[]
                        
#                         #Extract results by node
#                         for j in range(len(node_names)):
#                             Q_row_node.append(msx.MSXgetqual(0,int(node_ind[j]),int(species_ind[i])))
#                         results[species_names[i]]['node'].append(Q_row_node)
                        
#                         #Extract results by link
#                         for j in range(len(link_names)):
#                             Q_row_link.append(msx.MSXgetqual(1,int(link_ind[j]),int(species_ind[i])))
#                         results[species_names[i]]['link'].append(Q_row_link)
                        
                            
        
#         #After the simulation is complete go through the results one more time and
#         #convert the lists into dataframes
#         if (by_species=='no'):
#             #Nodes
#             for i in range(len(node_names)):
#                 results['node'][node_names[i]]=pd.DataFrame(results['node'][node_names[i]],index=T,columns=species_names)
            
#             #Links     
#             for i in range(len(link_names)):
#                 results['link'][link_names[i]]=pd.DataFrame(results['link'][link_names[i]],index=T,columns=species_names)
        
#         if (by_species=='yes'):
#             #Nodes
#             for i in range(len(species_names)):
#                 results[species_names[i]]['node']=pd.DataFrame(results[species_names[i]]['node'],index=T,columns=node_names)
            
#             #links
#             for i in range(len(species_names)):
#                 results[species_names[i]]['link']=pd.DataFrame(results[species_names[i]]['link'],index=T,columns=link_names)
    
#     if bin_read=='yes':
        
#         #Solve the quality of the model
#         msx.MSXsolveQ()
        
#         #Save quality results to binary file
#         #Add the process id to the binary file name so that multiple processes are
#         #not trying to read from the same file if it is run in parallel
#         filename='results_temp'+str(os.getpid())+'.bin'
#         msx.MSXsaveoutfile(filename)
        
#         #def MSXBinReader(filename, epanetinpfile):
        
#         #This code is from Jon Buckhardt that I lightly edited
#         duration=epa.ENgettimeparam(0)
#         with open(filename, 'rb') as fin:
#               ftype = '=f4'
#               idlen = 32
#               prolog = np.fromfile(fin, dtype = np.int32, count = 6)
#               magic1 = prolog[0]
#               version = prolog[1]
#               nnodes = prolog[2]
#               nlinks = prolog[3]
#               nspecies = prolog[4]
#               reportstep = prolog[5]
#               species_list = []
#               node_list = GetNodeNameList()
#               link_list = GetLinkNameList()
        
#               for i in range(nspecies):
#                       species_len = int(np.fromfile(fin, dtype = np.int32, count = 1))
#                       species_name = ''.join(chr(f) for f in np.fromfile(fin, dtype = np.uint8, count = species_len) if f!=0)
#                       species_list.append(species_name)
              
                
#               species_mass = []
#               for i in range(nspecies):
#                       species_mass.append(''.join(chr(f) for f in np.fromfile(fin, dtype = np.uint8, count = 16) if f != 0))
#               timerange = range(0, duration+1, reportstep)
              
#               tr = len(timerange)
              
#               row1 = ['node']*nnodes*len(species_list)+['link']*nlinks*len(species_list)
#               row2 = []
#               for i in [nnodes,nlinks]:
#                       for j in species_list:
#                             row2.append([j]*i)
#               row2 = [y for x in row2 for y in x]
#               row3 = [node_list for i in species_list] + [link_list for i in species_list]
#               row3 = [y for x in row3 for y in x]    
              
#               tuples = list(zip(row1, row2, row3))
#               index = pd.MultiIndex.from_tuples(tuples, names = ['type','species','name'])
              
#               try:
#                       data = np.fromfile(fin, dtype = np.dtype(ftype), count = tr*(len(species_list*(nnodes + nlinks))))
#                       data = np.reshape(data, (tr, len(species_list*(nnodes + nlinks))))
#               except Exception as e:
#                   print(e)
#                   print ("oops")
#               postlog = np.fromfile(fin, dtype = np.int32, count = 4)
#               offset = postlog[0]
#               numreport = postlog[1]
#               errorcode = postlog[2]
#               magicnew = postlog[3] 
#               if magic1 == magicnew:
#                   #print("Magic# Match")
#                   df_fin = pd.DataFrame(data.transpose(), index = index, columns = timerange)
#                   df_fin = df_fin.transpose()
#               else:
#                   print("Magic#s do not match!")
#             #return df_fin
            
#         #df is a multilevel index dataframe of all of the results
        
#         #Now I am going to repackage the results so that it fits with my struct structure
#         #Of how I was doing the results before. This may take a bit of time but I want 
#         #things how I want them:)
        
#         #Create the dictionary
#         results={}
        
#         #Go through all the nodes and put data from the dataframe into the correct place
#         #in the results dictionary
        
#         if nodes=='all':
#             nodes=GetNodeNameList()
        
#         if links=='all':
#             links=GetLinkNameList()
            
#         if species=='all':
#             species=GetSpeciesNameList()
            
        
        
#         if by_species=='no':
            
#             #Create a dictionary within the dictionary for nodes and links
#             results['node']={}
            
#             results['link']={}    
            
#             for i in range(len(nodes)):
#                 #Put the dataframe in the dictionary at the correct location
#                 results['node'][nodes[i]]=df_fin.loc[:,('node',species,nodes[i])]
#                 #Fix the index so it is no longer a multiindex
#                 results['node'][nodes[i]].columns=results['node'][nodes[i]].columns.droplevel(['type','name'])
            
#             for i in range(len(links)):
#                 #Put the dataframe in the dictionary at the correct location
#                 results['link'][links[i]]=df_fin.loc[:,('link',species,links[i])]
#                 #Fix the index so it is no longer a multiindex
#                 results['link'][links[i]].columns=results['link'][links[i]].columns.droplevel(['type','name'])
        
#         if by_species=='yes':
            
#             for i in range(len(species)):
#                 #Create a dictionary for that species
#                 results[species[i]]={}
                
#                 #Put the concentrations of the nodes of that species in the right place
#                 results[species[i]]['node']=df_fin.loc[:,('node',species[i],nodes)]
#                 #Fix the index so it is no longer a multiindex
#                 results[species[i]]['node'].columns=results[species[i]]['node'].columns.droplevel(['type','species'])
                
#                 #Put the concentrations of the links of that species in the right place
#                 results[species[i]]['link']=df_fin.loc[:,('link',species[i],links)]
#                 #Fix the index so it is no longer a multiindex
#                 results[species[i]]['link'].columns=results[species[i]]['link'].columns.droplevel(['type','species'])       
        
#         #Remove the 
#         try:
#             os.remove(filename)
#         except:
#             print('Error removing ' + filename)
    
#     return results 

# #Get a list of all the node names
# def GetNodeNameList():
#     node_names=[]
#     #Get the number of nodes- 0 for nodes
#     node_num=epa.ENgetcount(0)
#     #Get a list for the node id's
#     for i in range(node_num):
#         node_names.append(epa.ENgetnodeid(i+1))
#     #Get an array for the node indicies
#     #node_ind=np.linspace(1,node_num,node_num)
#     return node_names

# #Get a list of all link names
# def GetLinkNameList():
#     link_names=[]
#     #Get the number of nodes- 2 for links
#     link_num=epa.ENgetcount(2)
#     #Get a list for the node id's
#     for i in range(link_num):
#         link_names.append(epa.ENgetlinkid(i+1))
#     #Get an array for the node indicies
#     #node_ind=np.linspace(1,node_num,node_num)
#     return link_names



# #Get a list of all the species names
# def GetSpeciesNameList():
#     species_names=[]
#     #Get the number of species 3 for species
#     species_num=msx.MSXgetcount(3)
#     #Get a list for the species id's
#     for i in range(species_num):
#         species_names.append(msx.MSXgetID(3,i+1))
#     return species_names

# def GetConstantNameList():
#     #Get the name for each constant
#     constant_names=[]
#     #Get the number of constants
#     constants_num=msx.MSXgetcount(6)
#     for i in range(constants_num):
#         #Get the name of each specific constant, 6 for constant
#         constant_names.append(msx.MSXgetID(6,i+1))
#     return constant_names

# def TimeToCriticalValue(results,element_type='node',element='1',species='cNH2CL',crit_val=1.46):
#     #As currently written, assumes results are NOT by species and that the 
#     #critical value is decreasing, finding the value on the way down
    
#     element_results=results[element_type][element]
#     chlor=element_results.loc[:,species]
#     chlor=chlor[chlor>crit_val]
#     t_crit=np.max(chlor.index)
#     return t_crit

# def TimeToCriticalValueSeries(chlor,crit_val=1.46):
#     #Same as function above but takes a series as an input instead of the overall results dictionary
    
#     #As currently written, assumes results are NOT by species and that the 
#     #critical value is decreasing, finding the value on the way down
    
#     chlor=chlor[chlor>crit_val]
#     t_crit=np.max(chlor.index)
#     return t_crit

# def GetConstants(con_get):
#     #Returns a numpy array with the constants of a model
         
#     #Get the indicies of the constants of interest
#     inds=[]
#     for i in range(len(con_get)):
#         inds.append(msx.MSXgetindex(6,con_get[i]))
    
#     #Make an array holding the initial value for each constant
#     constants=np.zeros((len(inds),1))
#     #Populate that array with the initial value of each constant
#     #IMPORTANT: Requires that the input vector is the indicies starting from 1
#     #not starting from 0 which is done in the previous for loop
#     for i in range(len(inds)):
#         constants[i] = msx.MSXgetconstant(inds[i])
        
#     return constants

# def GetInitialConcentration(node,species):
#     #Inputs: Nodes of interest and species of interest
#     #The node input is the ID of the node not the index number
#     #Returns a numpy array with the initial concentration of the specified
#     #Species at the specified node
    
    
#     #Get the index of the specified node
#     node_ind=epa.ENgetnodeindex(node)
        
        
#     #Get the indicies of the species of interest
#     inds=[]
#     #Get the indicies of the species of interest
#     for i in range(len(species)):
#         inds.append(msx.MSXgetindex(3,species[i]))
    
#     #Make an array holding the initial value for each species
#     initial_con=np.zeros((len(inds),1))
    
#     #Populate that array with the initial value of each initial species at the 
#     #specified node, input to the function
#     for i in range(len(inds)):
#         initial_con[i] = msx.MSXgetinitqual(0,node_ind,inds[i])
        
#     return initial_con

        
# def SetConstants(con_get,given_constants):
#     #Set constants to specific values
#     #con_get is a list with the IDs of the constants to be varied
#     #given_constants is a numpy array of the values of the constants to be changed
#     #the order of IDs in con_get must be the same as the order of the values in
#     #given_constants
         
#     #Get the indicies of the constants of interest
#     inds=[]
#     for i in range(len(con_get)):
#         inds.append(msx.MSXgetindex(6,con_get[i]))
    
#     #Populate that array with the initial value of each constant
#     for i in range(len(inds)):
#         msx.MSXsetconstant(inds[i],given_constants[i])
        
# def SetInitialConcentration(node,species,init_val):
#     #Inputs: Nodes of interest and species of interest, and vector of species values
#     #The node input is the ID of the node not the index number
    
#     if (len(species)!=len(init_val)):
#         raise Exception('The length of species IDs  list and species value array are not equal')
    
#     #Get the index of the specified node
#     node_ind=epa.ENgetnodeindex(node)
          
#     #Get the indicies of the species of interest
#     inds=[]
#     for i in range(len(species)):
#         inds.append(msx.MSXgetindex(3,species[i]))
       
#     #Set the species of interest to the specified values
#     for i in range(len(inds)):
#         msx.MSXsetinitqual(0,node_ind,inds[i],init_val[i])
        
# def SetGlobalInitialConcentration(species,init_val):
    
    
#     #Get the number of nodes in the model
#     node_num=epa.ENgetcount(0)
    
#     #Get the number of links- 2 for links
#     link_num=epa.ENgetcount(2)
    
#     #Get the indicies of the species of interest
#     inds=[]
#     for i in range(len(species)):
#         inds.append(msx.MSXgetindex(3,species[i]))
       
#     #Loop through each node
#     #Set the species of interest to the specified values
#     #For each species
#     for i in range(len(inds)):
#         #For each node
#         for j in range(node_num):
#             #j+1 because epanet indicies start from 1 not 0 like python
#             msx.MSXsetinitqual(0,j+1,inds[i],init_val[i])
    
#     #Loop through each species
#     #Set the species of interest to the specified values
#     #For each species
#     for i in range(len(inds)):
#         #For each link
#         for j in range(link_num):
#             #j+1 because epanet indicies start from 1 not 0 like python
#             msx.MSXsetinitqual(1,j+1,inds[i],init_val[i])
        
    
        
# def GetAllNodeDemands():     
#     #Get the base demands for each node
#     #Get the number of nodes
#     node_num=epa.ENgetcount(0)
#     #Create a list to put the values
#     node_demands=[]
#     #Extract the demands from the model
#     for i in range(node_num):
#         node_demands.append(epa.ENgetnodevalue(i+1, 1))
#     #Turn the list into an array
#     node_demands=np.array(node_demands)
#     return node_demands

# def SetAllNodeDemands(given_demands):
#     #Get the number of nodes
#     node_num=epa.ENgetcount(0)
#     #Raise an error if the number of demands supplied does not match the
#     #number of nodes in the model
#     if (node_num!=len(given_demands)):
#         raise Exception('The number of demands provided dose not match the total number of nodes in the model')
#     #Set the demands in the model
#     for i in range(len(given_demands)):
#         epa.ENsetnodevalue(i+1, 1, given_demands[i])
        
# def SetNodeDemands(nodes,given_demands):
#     #Set baseline demands in specific nodes
#     for i in range(len(nodes)):
#         epa.ENsetnodevalue(epa.ENgetnodeindex(nodes[i]), 1, given_demands[i])
        
# def MonochloramineSetTemp(Temp,unit,temp_cons):
#     #This function changes the temperature-dependant model constants in the 
#     #Monochloramine Decay model (found in Wahman 2018, developed by others)
    
#     if unit=='F':
#         #Convert to Kelvin
#         Temp_k=(Temp-32)*(5/9)+273.15
#     if unit=='C':
#         #Convert to Kelvin
#         Temp_k=Temp+273.15
#     if unit=='K':
#         #It already is in Kelvin but change the variable name
#         Temp_k=Temp
        
#     #Set constants based on the temperature
    
#     #Create a list of the acceptable constants to be varied
#     temp_cons_acceptable=['k1','k2','k3','AC1','AC2','AC3','KNH4','KHOCL','KH2CO3','KHCO3','KW']
    
#     #Check to make sure the constants supplied are in that list
#     for k in range(len(temp_cons)):
#         if temp_cons[k] not in temp_cons_acceptable:
#             raise Exception('One of the supplied constant names does not exist in the model')
        
#     #Create a list which is the same length as temp_cons
#     temp_con_val_list=[None]*len(temp_cons)
    
#     #Loop through each value of temp_cons and populate temp_con_val_list
#     for i in range(len(temp_cons)):
    
#     #Formule for each temperature-dependant constant are found in Wahman 2018
        
#         if temp_cons[i]=='k1':
#             temp_con_val_list[i]=6.6*10**8*np.exp(-1510/Temp_k)
#         if temp_cons[i]=='k2':
#             temp_con_val_list[i]=1.38*10**8*np.exp(-8800/Temp_k)
#         if temp_cons[i]=='k3':
#             temp_con_val_list[i]=3.0*10**5*np.exp(-2010/Temp_k)
#         if temp_cons[i]=='AC1':
#             temp_con_val_list[i]=1.05*10**7*np.exp(-2169/Temp_k)
#         if temp_cons[i]=='AC2':
#             temp_con_val_list[i]=8.19*10**6*np.exp(-4026/Temp_k)
#         if temp_cons[i]=='AC3':
#             temp_con_val_list[i]=4.2*10**31*np.exp(-22144/Temp_k)
#         if temp_cons[i]=='KNH4':
#             temp_con_val_list[i]=10**-(1.03*10**-4*Temp_k**2-9.21*10**-2*Temp_k+27.6)
#         if temp_cons[i]=='KHOCL':
#             temp_con_val_list[i]=10**-(1.18*10**-4*Temp_k**2-7.86*10**-2*Temp_k+20.5)
#         if temp_cons[i]=='KH2CO3':
#             temp_con_val_list[i]=10**-(1.48*10**-4*Temp_k**2-9.39*10**-2*Temp_k+21.2)
#         if temp_cons[i]=='KHCO3':
#             temp_con_val_list[i]=10**-(1.19*10**-4*Temp_k**2-7.99*10**-2*Temp_k+23.6)
#         if temp_cons[i]=='KW':
#             temp_con_val_list[i]=10**-(1.5*10**-4*Temp_k**2-1.23*10**-1*Temp_k+37.3)
        
#     #Take the individual values and put them in an array   
#     temp_con_vals=np.array(temp_con_val_list)
    
#     #Set the constants in the model
#     SetConstants(temp_cons,temp_con_vals)

# def MonochloramineGetTempCon(Temp,unit,con):
#     #This function changes the temperature-dependant model constants in the 
#     #Monochloramine Decay model (found in Wahman 2018, developed by others)
    
#     #Input a vector of temperatures and get a vector of the desired constant
    
#     if unit=='F':
#         #Convert to Kelvin
#         Temp_k=(Temp-32)*(5/9)+273.15
#     if unit=='C':
#         #Convert to Kelvin
#         Temp_k=Temp+273.15
#     if unit=='K':
#         #It already is in Kelvin but change the variable name
#         Temp_k=Temp
        
#     #Set constants based on the temperature
    
#     #Formule for each temperature-dependant constant are found in Wahman 2018
#     if con=='k1':
#         out=6.6*10**8*np.exp(-1510/Temp_k)
#     if con=='k2':
#         out=1.38*10**8*np.exp(-8800/Temp_k)
#     if con=='k3':
#         out=3.0*10**5*np.exp(-2010/Temp_k)
#     if con=='AC1':
#         out=1.05*10**7*np.exp(-2169/Temp_k)
#     if con=='AC2':
#         out=8.19*10**6*np.exp(-4026/Temp_k)
#     if con=='AC3':
#         out=4.2*10**31*np.exp(-22144/Temp_k)
#     if con=='KNH4':
#         out=10**-(1.03*10**-4*Temp_k**2-9.21*10**-2*Temp_k+27.6)
#     if con=='KHOCL':
#         out=10**-(1.18*10**-4*Temp_k**2-7.86*10**-2*Temp_k+20.5)
#     if con=='KH2CO3':
#         out=10**-(1.48*10**-4*Temp_k**2-9.39*10**-2*Temp_k+21.2)
#     if con=='KHCO3':
#         out=10**-(1.19*10**-4*Temp_k**2-7.99*10**-2*Temp_k+23.6)
#     if con=='KW':
#         out=10**-(1.5*10**-4*Temp_k**2-1.23*10**-1*Temp_k+37.3)
    
#     return out

# def GenerateNormal(problem,n_sims):
#     #Takes a problem (defined by the SALib package) and generates parameters for 
#     #model runs based on normal distributions of each parameter where the
#     #mean is the mean/median of the upper/lower bounds specified and the standard
#     #deviation is set so that 2 standard deviations from the mean is the upper/lower bound
#     #of the value for the specified parameter
    
    
#     #Create an empty array of the size needed
#     norm_input=np.zeros((n_sims,problem['num_vars']))
#     rng=np.random.default_rng()
    
#     for i in range(problem['num_vars']):
        
#         #Mean is the middle of the upper and lower bounds specified by the problem
#         mean=problem['bounds'][i].mean()
#         #The standard deviation is set so that 2 standard deviations away from the
#         #mean is the upper and lower bounds of the range specified by the problem
#         sigma=(problem['bounds'][i].mean()-problem['bounds'][i][0])/2    
#         norm_input[:,i]=rng.normal(mean,sigma,n_sims)
    
#     return norm_input
        
# def ScaleMatrixAll(X):
#     #Scales a matrix using the min/max over all of the columns instead of by each column individually
#         return (X - X.min()) / (X.max() - X.min())
    
# def KMeansBestNum(scaled_2d,clust_num_test=10):
#         #Find best number of kmeans clusters
#         sil=[None]*(clust_num_test-1)
#         random_state=170
#         for i in range(1,clust_num_test):
#             n=i+1
#             #do kmeans clustering
#             y_pred = KMeans(n_clusters=n, random_state=random_state).fit_predict(scaled_2d)
#             #Calculate the silhouette scores
#             sil[i-1]=silhouette_score(scaled_2d,y_pred)
#         #Find the index where the sil score is the highest
#         z=np.where(sil==np.max(sil))[0]
#         num_clust_best=z[0]+2
#         #Do the clustering one more time with that number of clusters
#         y_pred = KMeans(n_clusters=num_clust_best, random_state=random_state).fit_predict(scaled_2d)
#         return y_pred
    
# def Network2DPlot(network,color_var,size_var,title,nodes,min_scale=30,max_scale=80,show_inds='all'):
        
#     #Scale Information
#     mult=max_scale-min_scale
#     #doing the plotting
#     if show_inds=='all':
#         show_inds=list(np.arange(0,len(nodes)))
#     node_sizes=(ScaleMatrixAll(size_var[show_inds])*mult)+min_scale
#     node_sizes=node_sizes.astype(float)
#     wntr.graphics.plot_network(network, pd.Series(color_var,index=nodes)[show_inds], node_size=node_sizes,title=title)
    

# def GenerateCorrDemands(group,n,n_samples,mean_group,corr_m):
    
#     #Assuming the same standard deviation for all nodes
#     std_all=np.ones((n_samples,1))*.1
    
#     #The correlation among nodes becomes:
#     corr_node=np.ones((n_samples,n_samples))
    
#     #Create correlation matrix for each node
#     for i in range(n_samples):
#         for j in range(n_samples):
#             if i!=j:
#                 corr_node[i,j]=corr_m[group[i],group[j]]
    
#     #Create array for the means to add to the results
#     group_arr=np.array(group)
#     mean_all=np.ones((n_samples,1))
#     for i in range(np.max(np.unique(group))+1):
#         mean_all[np.where(group_arr==i)[0]]=mean_group[i]
    
    
#     signal=[]
#     for i in range(len(std_all)):
#         signal.append(np.random.default_rng().normal(0,1,n))
    
#     # signal=np.random.default_rng().normal(0,1,(n,2))
#     # signal01=np.random.default_rng().normal(0,1,n)
#     # signal02=np.random.default_rng().normal(0,1,n)
    
    
#     std_m = np.identity(len(std_all))*std_all
    
#     # calc desired covariance (vc matrix)
#     cov_m = np.dot(std_m, np.dot(corr_node, std_m))
#     cky = cholesky(cov_m, lower=True)
    
#     corr_data = np.dot(cky,signal)
#     corr_data=corr_data+mean_all
    
#     #Transpose output so each row is each simulation and each column is a node
#     corr_data=corr_data.T
#     return corr_data

# def MorrisWallEvaluate(model_pickle,species):

#     results_model=model_pickle['results']
#     nodes=model_pickle['nodes']
#     links=model_pickle['links']
#     problem=model_pickle['problem']
#     param_values_model=model_pickle['param_values']
#     inp_file=model_pickle['inp_file']

    
    
#     #Extract the number of timesteps for which the model was computed
#     timesteps=len(results_model[0]['node'][nodes[0]].index)
#     timesteps_index=results_model[0]['node'][nodes[0]].index
    
#     #Create a dictionary to store the mu_star and sigma results for the model
#     morris_results={}
#     morris_results['mu_star']={}
#     morris_results['sigma']={}
    
#     morris_results['mu_star']['node']={}
#     morris_results['mu_star']['link']={}
    
#     morris_results['sigma']['node']={}
#     morris_results['sigma']['link']={}
    
    
    
#     age_results={}
#     age_mean={}
#     age_mean['node']=pd.DataFrame()
#     age_mean['link']=pd.DataFrame()
    
#     for l in range(len(nodes)):
#         print('Evaluating Node ' + str(l+1) + ' of ' +str(len(nodes)))
#         #Compute the morris values for each parameter for each timestep of the model
#         #Create an array to store the mu_star values at each timestep
#         mu_star_timestep=np.zeros((timesteps,problem['num_vars']))
#         sigma_timestep=np.zeros((timesteps,problem['num_vars']))
        
#         #Extract the model output results for that specific timestep
#         con_out=np.zeros((len(results_model),1))
#         for j in range(timesteps):
#             for i in range(len(results_model)):
#                 con_out[i]=results_model[i]['node'][nodes[l]].loc[timesteps_index[j],species]
            
#             #Compute morris results
#             a=morris_a.analyze(problem,param_values_model,con_out)
            
#             mu_star_timestep[j,:]=a['mu_star']
#             sigma_timestep[j,:]=a['sigma']
        
#         #Convert mu_star_timestep into a dataframe
#         mu_star_df=pd.DataFrame(mu_star_timestep,index=timesteps_index,columns=problem['names'])
#         sigma_df=pd.DataFrame(sigma_timestep,index=timesteps_index,columns=problem['names'])
        
#         morris_results['mu_star']['node'][nodes[l]]=mu_star_df
#         morris_results['sigma']['node'][nodes[l]]=sigma_df
        
#         #Loop through all of the simulation results and get the average
#         #water age for each timestep and each node
        
#         #Create a dataframe to put the results into
#         age_results[nodes[l]]=pd.DataFrame()
#         for i in range(len(results_model)):
#             age_results[nodes[l]]['S'+str(i+1)]=results_model[i]['node'][nodes[l]]['AGE']
        
#         age_mean['node'][nodes[l]]=age_results[nodes[l]].mean(axis=1)
        
#     for l in range(len(links)):
#         print('Evaluating Link ' + str(l+1) + ' of ' + str(len(links)))
#         #Compute the morris values for each parameter for each timestep of the model
#         #Create an array to store the mu_star values at each timestep
#         mu_star_timestep=np.zeros((timesteps,problem['num_vars']))
#         sigma_timestep=np.zeros((timesteps,problem['num_vars']))
        
#         #Extract the model output results for that specific timestep
#         con_out=np.zeros((len(results_model),1))
#         for j in range(timesteps):
#             for i in range(len(results_model)):
#                 con_out[i]=results_model[i]['link'][links[l]].loc[timesteps_index[j],species]
            
#             #Compute morris results
#             a=morris_a.analyze(problem,param_values_model,con_out)
            
#             mu_star_timestep[j,:]=a['mu_star']
#             sigma_timestep[j,:]=a['sigma']
        
#         #Convert mu_star_timestep into a dataframe
#         mu_star_df=pd.DataFrame(mu_star_timestep,index=timesteps_index,columns=problem['names'])
#         sigma_df=pd.DataFrame(sigma_timestep,index=timesteps_index,columns=problem['names'])
        
#         morris_results['mu_star']['link'][links[l]]=mu_star_df
#         morris_results['sigma']['link'][links[l]]=sigma_df
        
#         #Loop through all of the simulation results and get the average
#         #water age for each timestep and each node
        
#         #Create a dataframe to put the results into
#         age_results[links[l]]=pd.DataFrame()
#         for i in range(len(results_model)):
#             age_results[links[l]]['S'+str(i+1)]=results_model[i]['link'][links[l]]['AGE']
        
#         age_mean['link'][links[l]]=age_results[links[l]].mean(axis=1)
        
#     return morris_results,age_mean


    