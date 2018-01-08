"""
The wntr.graphics.curve module includes methods plot fragility curves and 
pump curves.
"""
import numpy as np
try:
    import matplotlib.pyplot as plt
except:
    pass
import logging

logger = logging.getLogger(__name__)

def plot_fragility_curve(FC, fill=True, key='Default',
                         title='Fragility curve', 
                         xmin=0, xmax=1, npoints=100, 
                         xlabel='x', 
                         ylabel='Probability of exceeding a damage state',
                         figsize=[8,4]):
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
    
    figsize : list (optional)
        Figure size (default = [8,4])
"""
    plt.figure(figsize=tuple(figsize))
    plt.title(title)
    x = np.linspace(xmin,xmax,npoints)
    for name, state in FC.states():
        try:
            dist=state.distribution[key]
            if fill:
                plt.fill_between(x,dist.cdf(x), label=name)
            else:
                plt.plot(x,dist.cdf(x), label=name)
        except:
            pass        
    plt.xlim((xmin,xmax))
    plt.ylim((0,1))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()

def plot_pump_curve(pump, title='Pump curve', 
                    xmin=0, xmax=None, ymin=0, ymax=None, 
                    xlabel='Head (m)', 
                    ylabel='Flow (m3/s)',
                    figsize=[8,4]):
    """
    Plot pump curve.
    
    Parameters
    -----------
    pump : wntr.scenario.Pump object
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
        X axis label (default = 'Head (m)')
    
    ylabel : string (optional)
        Y axis label (default = 'Flow (m3/s)')
    
    figsize : list (optional)
        Figure size (default = [8,4])
    """
    try:
        curve = pump.get_pump_curve()
    except:
        print("Pump "+pump.name+" has no curve")
        return
    
    plt.figure(figsize=tuple(figsize))
    plt.title(title)
    x = []
    y = []
    for pt in curve.points:
        x.append(pt[0])
        y.append(pt[1])
    plt.scatter(x,y)
    plt.plot(x,y, label=curve.name)    
    if xmax is None:
        xmax = max(x)
    if ymax is None:
        ymax = max(y)
    plt.xlim((xmin,xmax))
    plt.ylim((ymin,ymax))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    