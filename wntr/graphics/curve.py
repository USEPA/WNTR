"""
The wntr.graphics.curve module includes methods plot fragility curves and 
pump curves.
"""
import numpy as np
try:
    import matplotlib.pyplot as plt
except:
    plt = None
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
    
    fill : bool (optional)
        If true, fill area under the curve (default = True)
    
    key : string (optional)
        Fragility curve state distribution key (default = 'Default')
    
    title : string (optional)
        Plot title
    
    xmin : float (optional)
        X axis minimum (default = 0)
    
    xmax : float (optional)
        X axis maximum (default = 1)
    
    npoints : int (optional)
        Number of points (default = 100)
    
    xlabel : string (optional)
        X axis label (default = 'x')
    
    ylabel : string (optional)
        Y axis label (default = 'Probability of exceeding a damage state')
    
    ax : matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
        
    Returns
    ---------
    ax : matplotlib axes object
"""
    if plt is None:
        raise ImportError('matplotlib is required')
    
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
    
    return ax

def plot_pump_curve(pump, title='Pump curve', 
                    xmin=0, xmax=None, ymin=0, ymax=None, 
                    xlabel='Flow (m3/s)',
                    ylabel='Head (m)', 
                    ax=None):
    """
    Plot points in the pump curve along with the pump curve polynomial using 
    head curve coefficients (H = A - B*Q**C)
    
    Parameters
    -----------
    pump : wntr.network.elements.Pump object
        Pump
        
    title : string (optional)
        Plot title

    xmin : float (optional)
        X axis minimum (default = 0)
    
    xmax : float (optional)
        X axis maximum (default = None)
    
    ymin : float (optional)
        Y axis minimum (default = 0)
    
    ymax : float (optional)
        Y axis maximum (default = None)
    
    xlabel : string (optional)
        X axis label (default = 'Flow (m3/s)')
    
    ylabel : string (optional)
        Y axis label (default = 'Head (m)')
    
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

    if plt is None:
        raise ImportError('matplotlib is required')
    
    if ax is None: # create a new figure
        plt.figure(figsize=[8,4])
        ax = plt.gca()
        
    ax.set_title(title)
    
    Q = []
    H = []
    for pt in curve.points:
        Q.append(pt[0])
        H.append(pt[1])
 
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
    
    return ax