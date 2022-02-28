from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import numpy as np
import matplotlib.pylab as plt
import logging

logger = logging.getLogger(__name__)

def custom_colormap(N, colors=['blue','white','red'], name='custom'):
    """ 
    Create a custom colormap.  Default settings creates a colormap named 'custom'
    which transitions from blue to white to red.
    
    Parameters
    -----------
    N : int 
        Number of bins in the colormap.
        
    colors : list of colors (optional)
        Colors can be specified in any way understandable by 
        matplotlib.colors.ColorConverter.to_rgb().  
    
    name : str (optional)
        Name of the colormap
        
    Returns
    --------
    cmap : matplotlib.colors.LinearSegmentedColormap object
    """
    
    cmap = LinearSegmentedColormap.from_list(name=name, 
                                             colors = colors,
                                             N=N)
    return cmap

def random_colormap(N, colormap='jet', name='random', seed=None):
    """ 
    Create a random ordered colormap.  Default settings creates a colormap named 'random'
    using the jet colormap.
    
    Parameters
    -----------
    N : int 
        Number of bins in the colormap.
        
    colormap : str (optional)
        Name of matplotlib colormap
    
    name : str (optional)
        Name of the colormap
    
    seed : int or None
        Random seed
        
    Returns
    --------
    cmap : matplotlib.colors.ListedColormap object
    """
    if seed is not None:
        np.random.seed(seed)
    
    vals = np.arange(0,1,1/N) 
    np.random.shuffle(vals)
    cmap = plt.get_cmap(colormap)
    cmap_random = ListedColormap(cmap(vals), name=name)

    return cmap_random
