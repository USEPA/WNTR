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

def plot_fragility_curve(FC, fill=True, dist_key='Default',
                         title='Fragility curve', 
                         xmin=0, xmax=1, npoints=100, 
                         xlabel='x', 
                         ylabel='Probability of exceeding a damage state',
                         figsize=[8,4], dpi=100):
    """
    Plot fragility curve.
    """
    plt.figure(figsize=tuple(figsize), dpi=dpi)
    plt.title(title)
    x = np.linspace(xmin,xmax,npoints)
    for name, state in FC.states():
        try:
            dist=state.distribution[dist_key]
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
                    figsize=[8,4], dpi=100):
    """
    Plot pump curve.
    """
    plt.figure(figsize=tuple(figsize), dpi=dpi)
    plt.title(title)
    x = []
    y = []
    for pt in pump.curve.points:
        x.append(pt[0])
        y.append(pt[1])
    plt.scatter(x,y)
    plt.plot(x,y, label=pump.curve.name)    
    if xmax is None:
        xmax = max(x)
    if ymax is None:
        ymax = max(y)
    plt.xlim((xmin,xmax))
    plt.ylim((ymin,ymax))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    