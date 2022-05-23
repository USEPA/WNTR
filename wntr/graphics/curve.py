"""
The wntr.graphics.curve module includes methods plot fragility curves and 
pump curves.
"""
import numpy as np
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

def plot_fragility_curve(FC, fill=True, key='Default',
                         title='Fragility curve', 
                         xmin=0, xmax=1, npoints=100, 
                         xlabel='x', 
                         ylabel='Probability of exceeding a damage state',
                         ax=None):
    """
    Plot fragility curve.
    
    Parameters
    -----------
    FC : wntr.scenario.FragilityCurve object
        Fragility curve
    fill : bool, optional
        If true, fill area under the curve
    key : string, optional
        Fragility curve state distribution key
    title : string, optional
        Plot title
    xmin : float, optional
        X axis minimum 
    xmax : float, optional
        X axis maximum 
    npoints : int, optional
        Number of points 
    xlabel : string, optional
        X axis label
    ylabel : string, optional
        Y axis label
    ax : matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
        
    Returns
    ---------
    ax : matplotlib axes object
    """
    if ax is None: # create a new figure
        plt.figure(figsize=[8,4])
        ax = plt.gca()
        
    ax.set_title(title)
    
    x = np.linspace(xmin,xmax,npoints)
    for name, state in FC.states():
        try:
            dist=state.distribution[key]
            if fill:
                plt.fill_between(x, dist.cdf(x), label=name)
            else:
                plt.plot(x, dist.cdf(x), label=name)
        except:
            pass
        
    ax.set_xlim((xmin,xmax))
    ax.set_ylim((0,1))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    
    plt.show(block=False)
    
    return ax

def plot_pump_curve(pump, title='Pump curve', 
                    xmin=0, xmax=None, ymin=0, ymax=None, 
                    xlabel='Flow (m$^3$/s)',
                    ylabel='Head (m)', 
                    ax=None):
    """
    Plot points in the pump curve along with the pump curve polynomial using 
    head curve coefficients (H = A - B*Q**C)
    
    Parameters
    -----------
    pump : wntr.network.elements.Pump object
        Pump
    title : string, optional
        Plot title
    xmin : float, optional
        X axis minimum
    xmax : float, optional
        X axis maximum
    ymin : float, optional
        Y axis minimum
    ymax : float, optional
        Y axis maximum
    xlabel : string, optional
        X axis label
    ylabel : string, optional
        Y axis label 
    ax : matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
        
    Returns
    ---------
    ax : matplotlib axes object  
    """
    try:
        curve = pump.get_pump_curve()
    except:
        print("Pump "+pump.name+" has no curve")
        return
    
    if ax is None: # create a new figure
        plt.figure(figsize=[8,4])
        ax = plt.gca()
        
    ax.set_title(title)
    
    cdata = np.array(curve.points)
    Q = cdata[:,0]
    H = cdata[:,1]

    try:
        coeff = pump.get_head_curve_coefficients()
        A = coeff[0]
        B = coeff[1]
        C = coeff[2]
        
        Q_max = (A/B)**(1/C)
        q = np.linspace(0, Q_max, 50)
        h = A - B*q**C
        
        ax.plot(q, h, '--', linewidth=1)
    except:
        pass
    
    ax.plot(Q, H, 'o', label=curve.name)    
    
    ax.set_xlim((xmin,xmax))
    ax.set_ylim((ymin,ymax))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    
    plt.show(block=False)
    
    return ax

def plot_tank_volume_curve(tank, title='Tank volume curve', 
                    ax=None):
    """
    Plots a tank volume curve and the corresponding axi-symmetric tank profile shape
    
    Parameters
    -----------
    tank : wntr.network.elements.Tank object
        Tank 
    title : string, optional
        Plot title
    ax : matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with two subplots 
        will be used)
        
    Returns
    ---------
    ax : matplotlib axes object
        ax[0] is the left hand plot, ax[1] is the right hand plot
    """
    curve = tank.vol_curve
    
    if curve is None:
        print("Tank "+tank.name+" has no volume curve")
        return

    if ax is None: # create a new figure
        fig,ax = plt.subplots(1,2,figsize=[12,4])

    cdata = np.array(curve.points)
    L = cdata[:,0]
    V = cdata[:,1]
    
    V_min_level = tank.get_volume(tank.min_level)
    V_max_level = tank.get_volume(tank.max_level)

    ax[0].plot(L, V, '-o', linewidth=1,label="volume curve")
    ax[0].plot([tank.min_level,tank.min_level], [V_min_level,V_max_level],'-.',
        label="min level",color='r')
    ax[0].plot([tank.max_level,tank.max_level], [V_min_level,V_max_level],'-.',
        label="max level",color='r')
    ax[0].grid("on")
    ax[0].set_xlabel("Tank level (m)")
    ax[0].set_ylabel("Tank volume (m$^3$)")
    ax[0].set_title(title)
    ax[0].legend()
    
    # calculate the tank profile assuming an axi-symmetric tank
    d = []
    l = []
    #d.append(0.0)
    #d.append(tank.diameter)
    #d.append(tank.diameter)
    #l.append(0.0)
    #l.append(0.0)
    #l.append(tank.min_level)
    lev0 = L[0]
    vol0 = V[0]
    for vol,lev in zip(V[1:],L[1:]):
        dn = np.sqrt(4.0*(vol-vol0)/(np.pi * (lev-lev0)))
        l.append(lev0)
        l.append(lev)
        d.append(dn)
        d.append(dn)
        lev0 = lev
        vol0 = vol
    #l.append(l[-1])
    #d.append(0.0)
    
    ax[1].plot(np.array(d)/2,l,label="tank profile")
    max_d = max([tank.diameter,max(d)])
    ax[1].plot([0.0,max_d/2.0],[tank.min_level,tank.min_level],'-.',
        label="min level",color='r')
    ax[1].plot([0.0,max_d/2.0],[tank.max_level,tank.max_level],'-.',
        label="max level",color='r')
    #ax[1].plot([0.0,max_d/2.0],[0.0,0.0],'-.',label='elevation={0:5.2f}m'.format(tank.elevation),color='k')
    ax[1].grid("on")
    ax[1].set_xlabel("Equivalent axisymmetric tank radius (m)")
    ax[1].set_ylabel("Tank level (m)")
    ax[1].set_title("Geometric tank profile")
    
    xlim = list(ax[1].get_xlim())
    ylim = list(ax[1].get_ylim())
    if np.diff(xlim) > np.diff(ylim):
        ylim[1] = ylim[0] + (xlim[1]-xlim[0])
    else:
        xlim[1] = xlim[0] + (ylim[1] - ylim[0])
    ax[1].set_xlim(xlim)
    ax[1].set_ylim(ylim)
    ax[1].legend()
    
    plt.show(block=False)
    
    return ax
