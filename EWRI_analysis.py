import epanetlib as en
import matplotlib.pyplot as plt
import numpy as np
from sympy.physics import units
import pickle 
import pandas as pd
import sys
import matplotlib

def make_cmap(colors, position=None, bit=False):
    '''
    make_cmap takes a list of tuples which contain RGB values. The RGB
    values may either be in 8-bit [0 to 255] (in which bit must be set to
    True when called) or arithmetic [0 to 1] (default). make_cmap returns
    a cmap with equally spaced colors.
    Arrange your tuples so that the first color is the lowest value for the
    colorbar and the last is the highest.
    position contains values from 0 to 1 to dictate the location of each color.
    '''
    import matplotlib as mpl
    bit_rgb = np.linspace(0,1,256)
    if position == None:
        position = np.linspace(0,1,len(colors))
    else:
        if len(position) != len(colors):
            sys.exit("position length must be the same as colors")
        elif position[0] != 0 or position[-1] != 1:
            sys.exit("position must start with 0 and end with 1")
    if bit:
        for i in range(len(colors)):
            colors[i] = (bit_rgb[colors[i][0]],
                         bit_rgb[colors[i][1]],
                         bit_rgb[colors[i][2]])
    cdict = {'red':[], 'green':[], 'blue':[]}
    for pos, color in zip(position, colors):
        cdict['red'].append((pos, color[0], color[0]))
        cdict['green'].append((pos, color[1], color[1]))
        cdict['blue'].append((pos, color[2], color[2]))

    cmap = mpl.colors.LinearSegmentedColormap('my_colormap',cdict,256)
    return cmap

def shiftedColorMap(cmap, start=0, midpoint=0.5, stop=1.0, name='shiftedcmap'):
    '''
    Function to offset the "center" of a colormap. Useful for
    data with a negative min and positive max and you want the
    middle of the colormap's dynamic range to be at zero

    Input
    -----
      cmap : The matplotlib colormap to be altered
      start : Offset from lowest point in the colormap's range.
          Defaults to 0.0 (no lower ofset). Should be between
          0.0 and `midpoint`.
      midpoint : The new center of the colormap. Defaults to 
          0.5 (no shift). Should be between 0.0 and 1.0. In
          general, this should be  1 - vmax/(vmax + abs(vmin))
          For example if your data range from -15.0 to +5.0 and
          you want the center of the colormap at 0.0, `midpoint`
          should be set to  1 - 5/(5 + 15)) or 0.75
      stop : Offset from highets point in the colormap's range.
          Defaults to 1.0 (no upper ofset). Should be between
          `midpoint` and 1.0.
    '''
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt

    cdict = {
        'red': [],
        'green': [],
        'blue': [],
        'alpha': []
    }

    # regular index to compute the colors
    reg_index = np.linspace(start, stop, 257)

    # shifted index to match the data
    shift_index = np.hstack([
        np.linspace(0.0, midpoint, 128, endpoint=False), 
        np.linspace(midpoint, 1.0, 129, endpoint=True)
    ])

    for ri, si in zip(reg_index, shift_index):
        r, g, b, a = cmap(ri)

        cdict['red'].append((si, r, r))
        cdict['green'].append((si, g, g))
        cdict['blue'].append((si, b, b))
        cdict['alpha'].append((si, a, a))

    newcmap = matplotlib.colors.LinearSegmentedColormap(name, cdict)
    plt.register_cmap(cmap=newcmap)

    return newcmap
    
    
plt.close('all')

matplotlib.rc('xtick', labelsize=16) 
matplotlib.rc('ytick', labelsize=16)
font = {'family' : 'normal',
        'weight' : 'normal',
        'size'   : 16}
matplotlib.rc('font', **font)


# Define water pressure unit in meters
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart
R = 200*float((units.gallon/units.day)/(units.m**3/units.day)) # average volume of water consumed per capita per day, m3/day

nzd_cutoff = 10*float((units.gallon/units.minute)/(units.m**3/units.s)) # average volume of water consumed per capita per day, m3/day


inp_file = 'networks/Net6_mod.inp'

# Create a water network model
wn = en.network.WaterNetworkModel()
parser = en.network.ParseWaterNetwork()
parser.read_inp_file(wn, inp_file)

pyomo_results = pickle.load(open('all_scenario_results_15hr.pickle', 'rb'))
te = pd.Timedelta(hours=2)
ta = pd.Timedelta(hours=17) 
action='15hr'

pump_stations = {
#    '1': ['PUMP-3829'], # Controls TANK-3326
    '2': ['PUMP-3830', 'PUMP-3831', 'PUMP-3832', 'PUMP-3833', 'PUMP-3834'], #  Controls TANK-3325, Pump station 2 is connected to the reservoir
    '3': ['PUMP-3835', 'PUMP-3836', 'PUMP-3837', 'PUMP-3838'], # Controls TANK-3333
    '4': ['PUMP-3839', 'PUMP-3840', 'PUMP-3841'], # Controls TANK-3333
#    '5': ['PUMP-3842', 'PUMP-3843', 'PUMP-3844'], # Controls TANK-3335
#    '6': ['PUMP-3845', 'PUMP-3846'], # Controls TANK-3336
#    '7': ['PUMP-3847', 'PUMP-3848'], # Controls TANK-3337
    '8': ['PUMP-3849', 'PUMP-3850', 'PUMP-3851', 'PUMP-3852', 'PUMP-3853'], # Controls TANK-3337
#    '9': ['PUMP-3854', 'PUMP-3855', 'PUMP-3856'], # TANK-3340
#    '10': ['PUMP-3857', 'PUMP-3858', 'PUMP-3859'], # Controls TANK-3341
#    '11': ['PUMP-3860', 'PUMP-3861', 'PUMP-3862'], # Controls TANK-3342
#    '12': ['PUMP-3863', 'PUMP-3864', 'PUMP-3865', 'PUMP-3866'], # Controls TANK-3343
#    '13': ['PUMP-3867', 'PUMP-3868', 'PUMP-3869'], # Controls TANK-3346
#    '14': ['PUMP-3870', 'PUMP-3871'], # Controls TANK-3347
    '15': ['PUMP-3872', 'PUMP-3873', 'PUMP-3874'], # Controls TANK-3349
#    '16': ['PUMP-3875', 'PUMP-3876', 'PUMP-3877'], # Controls TANK-3348
#    '17': ['PUMP-3878'], # Controls TANK-3352
#    '18': ['PUMP-3879', 'PUMP-3880', 'PUMP-3881'], # Controls TANK-3353
#    '19': ['PUMP-3882', 'PUMP-3883', 'PUMP-3884'], # Controls TANK-3355
#    '20': ['PUMP-3885'], # Controls TANK-3354
#    '21': ['PUMP-3886', 'PUMP-3887', 'PUMP-3888'], # Controls TANK-3356
#    '22': ['PUMP-3889'], # No curve, only power 15?
    'ALL': []}
#    'None': []}

nzd_junctions = wn.query_node_attribute('base_demand', np.greater, nzd_cutoff, node_type=en.network.Junction).keys()

pressure_lower_bound = 30*float(units.psi/units.waterpressure) # psi to m

plt.figure()
linecolor = ['r','k','g','m']
line = 0
for k,v in pump_stations.iteritems():
    
    # FDV, scenario k, time t
    FDV_kt = pyomo_results[k].node.loc[nzd_junctions, 'demand'].sum(level=1)/pyomo_results[k].node.loc[nzd_junctions, 'expected_demand'].sum(level=1)
    FDV_kt.index = FDV_kt.index.format() 
    if k is 'ALL':
        FDV_kt.plot(label='Average', color='b', linewidth=2.0, legend=False)
    else:
        FDV_kt.plot(label='Average', color='k', linewidth=2.0, legend=False)
        #FDV_kt.plot(label='Average', color=linecolor[line], linewidth=2.0, legend=False)
        line = line+1
        
    plt.hold(True)
     
plt.ylim( (0.7, 1.05) )
plt.ylabel('FDV')
plt.savefig('FDVkt_StageTransition_'+ action +'.png')

R = (1,0,0)
Y = (1,1,0.5)
G = (0,1,0)

#cmap = shiftedColorMap(plt.cm.RdYlGn, start=0.15, midpoint=0.5, stop=0.85, name='shrunk')
cmap = make_cmap([R,Y,G])
cmap_reverse = make_cmap([G,Y,R])
cmap_binary = shiftedColorMap(plt.cm.binary, start=0.3, midpoint=0.5, stop=0.6, name='binary')

RV_n = {} # Requested volume, node n
EV_n = {} # Expected volume, node n
count_nodes = {}
count_people = {}
graphic = False

minFDV_k = {}
time_to_disruption_k = {}
time_to_recovery_k = {}
nTanks_low_k = {}
for k,v in pump_stations.iteritems():
    print k
    plt.close('all')
    
    # FDV, scenario k, node n, time t
    FDV_knt = pyomo_results[k].node.loc[nzd_junctions, 'demand']/pyomo_results[k].node.loc[nzd_junctions, 'expected_demand']
    
    # Time to disruption, min state, scenario k, node n
    minFDV_kn = {}
    time_to_disruption_kn = {}
    time_to_recovery_kn = {}
    count_nodes[k] = 0
    count_people[k] = 0
    for j in nzd_junctions:
        temp = FDV_knt[j]
        temp = temp.round(decimals=3)
        val = temp.min()
        td = temp.idxmin()
        tr = temp[td::].idxmax()
        if val < 0.98:
            minFDV_kn[j] = val
            time_to_disruption_kn[j] = (td-te).hours
            time_to_recovery_kn[j] = (tr-td).hours
    
        if val < 0.98:
            count_nodes[k] = count_nodes[k] + 1
            #people = pyomo_results[k].node.loc[j, 'expected_demand'].sum()*(60*60*24)/R
            #count_people[k] = count_people[k] + people
    if graphic:
        font = {'family' : 'normal',
            'weight' : 'normal',
            'size'   : 12}
        matplotlib.rc('font', **font)

        en.network.draw_graph(wn, node_attribute=minFDV_kn, node_size=40, node_range=[0,1], node_cmap=cmap, figsize=(12,9), title='Min FDV, Power outage at pump station ' + k)
        plt.savefig('minFDVkn_PumpStation' + k +'_'+ action+'.png', format='png', dpi=500)
        
        #en.network.draw_graph(wn, node_attribute=time_to_disruption_kn, node_size=40, node_range=[0,15], node_cmap=cmap, figsize=(20,15), title='Time to disruption, Power outage at pump station ' + k)
        #plt.savefig('Td_PumpStation' + k +'_'+ action+'.png', format='png', dpi=400)
        
        #en.network.draw_graph(wn, node_attribute=time_to_recovery_kn, node_size=40, node_range=[0,15], node_cmap=cmap, figsize=(20,15), title='Time to recovery, Power outage at pump station ' + k)
        #plt.savefig('Tr_PumpStation' + k +'_'+ action+'.png', format='png', dpi=400)
        
    font = {'family' : 'normal',
        'weight' : 'normal',
        'size'   : 16}
    matplotlib.rc('font', **font)
    # FVD, node n (sum over all scenarios)
    RV_n[k] = pyomo_results[k].node.loc[nzd_junctions, 'demand'].sum(level=0)
    EV_n[k] = pyomo_results[k].node.loc[nzd_junctions, 'expected_demand'].sum(level=0)
    
    # FDV, scenario k, time t
    FDV_kt = pyomo_results[k].node.loc[nzd_junctions, 'demand'].sum(level=1)/pyomo_results[k].node.loc[nzd_junctions, 'expected_demand'].sum(level=1)
    
    # Time to disruption, min state, scenario k
    temp = FDV_kt
    temp = temp.round(decimals=3)
    val = temp.min()
    td = temp.idxmin()
    tr = temp[td::].idxmax()
    minFDV_k[k] = val
    time_to_disruption_k[k] = (td-te).hours
    time_to_recovery_k[k] = (tr-td).hours

    if graphic:
        # State Transition Plot
        FDV_knt = FDV_knt.unstack().T 
        FDV_knt.index = FDV_knt.index.format() 
        FDV_knt.plot(legend=False, colormap=cmap_binary)
        plt.hold(True)
        FDV_kt.index = FDV_kt.index.format() 
        FDV_kt.plot(label='Average', color='b', linewidth=3.0, legend=False)
        plt.ylim( (-0.05, 1.05) )
        #plt.legend(loc='best')
        plt.ylabel('FDV')
        #plt.title('Power outage at pump station ' + k)
        plt.savefig('FDVknt_StageTransition_PumpStation' + k +'_'+ action+'.png', format='png', dpi=500)
         
        # Pressure in the tanks
        nTanks_low_k[k] = 0
        plt.figure()
        for tank_name, tank in wn.nodes(en.network.Tank):
            tank_pressure = pyomo_results[k].node['pressure'][tank_name]
            if tank_pressure.min() < 2:
                tank_pressure.index = tank_pressure.index.format() 
                tank_pressure.plot(label=tank_name, color='k')
                plt.hold(True)
                nTanks_low_k[k] = nTanks_low_k[k] + 1
        plt.ylim([0, 10])
        plt.ylabel('Tank Pressure (m)')
        #plt.title('Power outage at pump station ' + k)
        plt.savefig('Tanks_PumpStation' + k +'_'+ action+'.png', format='png', dpi=500)
    
RV_sum = {}
EV_sum = {}
FDV_n = {}
gall = {}
for k,v in pump_stations.iteritems():
    RV_sum[k] = RV_n[k].sum(axis=0)
    EV_sum[k] = EV_n[k].sum(axis=0)
    FDV_n[k] = RV_sum[k]/EV_sum[k]
    gall[k] = sum(EV_sum.values()) - sum(RV_sum.values())
    
#en.network.draw_graph(wn, node_attribute=dict(FDV_n), node_size=40, node_range=[0.5,1], node_cmap=cmap, figsize=(20,15), title='FDV')

# Convert pump stations to node locations to plot
minFDV_k2 = {}
count_nodes2 = {}
try:
    del pump_stations['ALL']
except:
    pass
for k,v in pump_stations.iteritems():
    link_name = v[0]
    link = wn.get_link(link_name)
    #minFDV_k2[link.end_node()] = minFDV_k[k] 
    if minFDV_k[k] > 0.98:
        minFDV_k2[link.end_node()] = 1
    else:
        minFDV_k2[link.end_node()] = 0
    count_nodes2[link.end_node()] = count_nodes[k]

pipe_attr = wn.get_link_attribute('length', link_type=en.network.Pipe)
en.network.draw_graph(wn, node_attribute=minFDV_k2, link_attribute=pipe_attr, node_size=80, node_cmap=cmap, link_cmap = cmap_binary, figsize=(20,15), title='Minimum State')
plt.savefig('MinimumState_'+ action+'.png', format='png', dpi=500)
en.network.draw_graph(wn, node_attribute=count_nodes2, node_size=80, node_cmap=cmap_reverse, figsize=(20,15), title='Disrupted Nodes')
plt.savefig('DisruptedNodes_'+action+'.png', format='png', dpi=500)
