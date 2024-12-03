
import os
import sys
import unittest
import warnings
from os.path import abspath, dirname, isfile, join

import networkx as nx
import matplotlib.pylab as plt
import matplotlib
from wntr.graphics.color import custom_colormap
import pandas as pd
import numpy as np
import wntr

testdir = dirname(abspath(str(__file__)))
test_datadir = join(testdir, "networks_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")


class TestGraphics(unittest.TestCase):
    def test_plot_network1(self):
        filename = abspath(join(testdir, "plot_network1.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        wntr.graphics.plot_network(wn)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network2(self):
        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        # undirected
        filename = abspath(join(testdir, "plot_network2_undirected.png"))
        if isfile(filename):
            os.remove(filename)

        wntr.graphics.plot_network(
            wn, node_attribute="elevation", link_attribute="length"
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))
        
        # directed
        filename = abspath(join(testdir, "plot_network2_directed.png"))
        if isfile(filename):
            os.remove(filename)

        wntr.graphics.plot_network(
            wn, node_attribute="elevation", link_attribute="length", directed=True
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network3(self):
        filename = abspath(join(testdir, "plot_network3.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        wntr.graphics.plot_network(
            wn,
            node_attribute=["11", "21"],
            link_attribute=["112", "113"],
            link_labels=True,
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network4(self):
        filename = abspath(join(testdir, "plot_network4.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net1.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        wntr.graphics.plot_network(
            wn,
            node_attribute={"11": 5, "21": 10},
            link_attribute={"112": 3, "113": 9},
            node_labels=True,
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network5(self):
        filename = abspath(join(testdir, "plot_network5.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        pop = wntr.metrics.population(wn)

        wntr.graphics.plot_network(
            wn, node_attribute=pop, node_range=[0, 500], title="Population"
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_network6(self):
        # legend
        filename = abspath(join(testdir, "plot_network6.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        wntr.graphics.plot_network(
            wn, node_attribute="elevation", link_attribute="diameter", 
            add_colorbar=True, legend=True
        )
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))
    
    def test_plot_network_options(self):
        # NOTE:to compare with the old plot_network set compare=True.
        #   this should be set to false for regular testing
        compare = False
        
        cmap = matplotlib.colormaps['viridis']
        
        inp_file = join(ex_datadir, "Net6.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        
        random_node_values = pd.Series(
            np.random.rand(len(wn.node_name_list)), index=wn.node_name_list)
        random_link_values = pd.Series(
            np.random.rand(len(wn.link_name_list)), index=wn.link_name_list)
        random_pipe_values = pd.Series(
            np.random.rand(len(wn.pipe_name_list)), index=wn.pipe_name_list)
        random_node_dict_subset = dict(random_node_values.iloc[:10])
        random_link_dict_subset = dict(random_link_values.iloc[:10])
        node_list = list(wn.node_name_list[:10])
        link_list = list(wn.link_name_list[:10])
        
        kwarg_list = [
            {"node_attribute": "elevation",
             "node_range": [0,20],
             "node_alpha": 0.5,
             "node_colorbar_label": "test_label"},
            {"link_attribute": "diameter",
             "link_range": [0,None],
             "link_alpha": 0.5,
             "link_colorbar_label": "test_label"},
            {"link_attribute": "diameter",
            "node_attribute": "elevation"},
            {"node_labels": True,
             "link_labels": True},
            {"node_attribute": "elevation",
             "add_colorbar": False},
            {"link_attribute": "diameter",
             "add_colorbar": False},
            {"node_attribute": node_list},
            {"node_attribute": random_node_values},
            {"node_attribute": random_node_dict_subset},
            {"link_attribute": link_list},
            {"link_attribute": random_link_values},
            {"link_attribute": random_link_dict_subset},
            {"directed": True},
            {"link_attribute": random_pipe_values,
             "node_size": 0,
             "link_cmap": cmap,
             "link_range": [0,1],
             "link_width": 1.5},
        ]
        
        for kwargs in kwarg_list:
            filename = abspath(join(testdir, "plot_network_options.png"))
            if isfile(filename):
                os.remove(filename)
            if compare:
                fig, ax = plt.subplots(1,2)
                wntr.graphics.plot_network(wn, ax=ax[0], title="GIS plot_network", **kwargs)
                plot_network_nx(wn, ax=ax[1], title="NX plot_network", **kwargs)
                fig.savefig(filename, format="png")
                plt.close(fig)
            else:
                wntr.graphics.plot_network(wn, **kwargs)
                plt.savefig(filename, format="png")
                plt.close()
                
            self.assertTrue(isfile(filename))
            os.remove(filename)
            

    def test_plot_interactive_network1(self):

        filename = abspath(join(testdir, "plot_interactive_network1.html"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)

        plt.figure()
        wntr.graphics.plot_interactive_network(
            wn, node_attribute=["107", "123"], filename=filename, auto_open=False
        )

        self.assertTrue(isfile(filename))

    def test_plot_leaflet_network1(self):

        filename = abspath(join(testdir, "plot_leaflet_network1.html"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        longlat_map = {"Lake": (-106.6587, 35.0623), "219": (-106.5248, 35.1918)}
        wn2 = wntr.morph.convert_node_coordinates_to_longlat(wn, longlat_map)

        plt.figure()
        wntr.graphics.plot_leaflet_network(
            wn2,
            node_attribute="elevation",
            link_attribute="length",
            add_legend=True,
            filename=filename,
        )

        self.assertTrue(isfile(filename))

    def test_network_animation1(self):
        filename = abspath(join(testdir, "plot_leaflet_network1.html"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()

        pressure = results.node["pressure"]
        flowrate = results.link["flowrate"]
        anim = wntr.graphics.network_animation(
            wn, node_attribute=pressure, link_attribute=flowrate, repeat=True
        )

        from matplotlib.animation import FuncAnimation

        self.assertTrue(isinstance(anim, FuncAnimation))

    def test_plot_fragility_curve1(self):
        from scipy.stats import lognorm

        filename = abspath(join(testdir, "plot_fragility_curve1.png"))
        if isfile(filename):
            os.remove(filename)

        FC = wntr.scenario.FragilityCurve()
        FC.add_state("Minor", 1, {"Default": lognorm(0.5, scale=0.3)})
        FC.add_state("Major", 2, {"Default": lognorm(0.5, scale=0.7)})

        plt.figure()
        wntr.graphics.plot_fragility_curve(FC)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_pump_curve1(self):
        filename = abspath(join(testdir, "plot_pump_curve1.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(ex_datadir, "Net3.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        pump = wn.get_link("10")

        plt.figure()
        wntr.graphics.plot_pump_curve(pump)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

    def test_plot_tank_curve(self):
        filename = abspath(join(testdir, "plot_tank_curve.png"))
        if isfile(filename):
            os.remove(filename)

        inp_file = join(test_datadir, "Anytown_multipointcurves.inp")
        wn = wntr.network.WaterNetworkModel(inp_file)
        tank_w_curve = wn.get_node("41")
        tank_no_curve = wn.get_node("42")

        plt.figure()
        shouldBeAxis = wntr.graphics.plot_tank_volume_curve(tank_w_curve)
        plt.savefig(filename, format="png")
        plt.close()

        self.assertTrue(isfile(filename))

        shouldBeNone = wntr.graphics.plot_tank_volume_curve(tank_no_curve)
        self.assertTrue(shouldBeNone is None)

    def test_custom_colormap(self):
        cmp = wntr.graphics.custom_colormap(
            3, colors=["blue", "white", "red"], name="custom"
        )
        self.assertEqual(cmp.N, 3)
        self.assertEqual(cmp.name, "custom")
        
        
# old plotting function using networkx backend to compare with geopandas
def plot_network_nx(wn, node_attribute=None, link_attribute=None, title=None,
               node_size=20, node_range=[None,None], node_alpha=1, node_cmap=None, node_labels=False,
               link_width=1, link_range=[None,None], link_alpha=1, link_cmap=None, link_labels=False,
               add_colorbar=True, node_colorbar_label='Node', link_colorbar_label='Link', 
               directed=False, ax=None, show_plot=True, filename=None):
    """
    Plot network graphic
	
    Parameters
    ----------
    wn : wntr WaterNetworkModel
        A WaterNetworkModel object
		
    node_attribute : None, str, list, pd.Series, or dict, optional
	
        - If node_attribute is a string, then a node attribute dictionary is
          created using node_attribute = wn.query_node_attribute(str)
        - If node_attribute is a list, then each node in the list is given a 
          value of 1.
        - If node_attribute is a pd.Series, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float. 
        - If node_attribute is a dict, then it should be in the format
          {nodeid: x} where nodeid is a string and x is a float
    
	link_attribute : None, str, list, pd.Series, or dict, optional
	
        - If link_attribute is a string, then a link attribute dictionary is
          created using edge_attribute = wn.query_link_attribute(str)
        - If link_attribute is a list, then each link in the list is given a 
          value of 1.
        - If link_attribute is a pd.Series, then it should be in the format
          {linkid: x} where linkid is a string and x is a float. 
        - If link_attribute is a dict, then it should be in the format
          {linkid: x} where linkid is a string and x is a float.
		  
    title: str, optional
        Plot title 

    node_size: int, optional
        Node size 

    node_range: list, optional
        Node color range ([None,None] indicates autoscale)
        
    node_alpha: int, optional
        Node transparency
        
    node_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Node colormap 
        
    node_labels: bool, optional
        If True, the graph will include each node labelled with its name. 
        
    link_width: int, optional
        Link width
		
    link_range : list, optional
        Link color range ([None,None] indicates autoscale)
		
    link_alpha : int, optional
        Link transparency
    
    link_cmap: matplotlib.pyplot.cm colormap or list of named colors, optional
        Link colormap
        
    link_labels: bool, optional
        If True, the graph will include each link labelled with its name.
        
    add_colorbar: bool, optional
        Add colorbar

    node_colorbar_label: str, optional
        Node colorbar label
        
    link_colorbar_label: str, optional
        Link colorbar label
        
    directed: bool, optional
        If True, plot the directed graph
    
    ax: matplotlib axes object, optional
        Axes for plotting (None indicates that a new figure with a single 
        axes will be used)
    
    show_plot: bool, optional
        If True, show plot with plt.show()
    
    filename : str, optional
        Filename used to save the figure
        
    Returns
    -------
    ax : matplotlib axes object  
    """
    
    def _format_node_attribute(node_attribute, wn):
    
        if isinstance(node_attribute, str):
            node_attribute = wn.query_node_attribute(node_attribute)
        if isinstance(node_attribute, list):
            node_attribute = dict(zip(node_attribute,[1]*len(node_attribute)))
        if isinstance(node_attribute, pd.Series):
            node_attribute = dict(node_attribute)
        
        return node_attribute

    def _format_link_attribute(link_attribute, wn):
        
        if isinstance(link_attribute, str):
            link_attribute = wn.query_link_attribute(link_attribute)
        if isinstance(link_attribute, list):
            link_attribute = dict(zip(link_attribute,[1]*len(link_attribute)))
        if isinstance(link_attribute, pd.Series):
            link_attribute = dict(link_attribute)
                
        return link_attribute

    if ax is None: # create a new figure
        plt.figure(facecolor='w', edgecolor='k')
        ax = plt.gca()
        
    # Graph
    G = wn.to_graph()
    if not directed:
        G = G.to_undirected()

    # Position
    pos = nx.get_node_attributes(G,'pos')
    if len(pos) == 0:
        pos = None

    # Define node properties
    add_node_colorbar = add_colorbar
    if node_attribute is not None:
        
        if isinstance(node_attribute, list):
            if node_cmap is None:
                node_cmap = ['red', 'red']
            add_node_colorbar = False
        
        if node_cmap is None:
            node_cmap = plt.get_cmap('Spectral_r')
        elif isinstance(node_cmap, list):
            if len(node_cmap) == 1:
                node_cmap = node_cmap*2
            node_cmap = custom_colormap(len(node_cmap), node_cmap)  
         
        node_attribute = _format_node_attribute(node_attribute, wn)
        nodelist,nodecolor = zip(*node_attribute.items())

    else:
        nodelist = None
        nodecolor = 'k'
    
    add_link_colorbar = add_colorbar
    if link_attribute is not None:
        
        if isinstance(link_attribute, list):
            if link_cmap is None:
                link_cmap = ['red', 'red']
            add_link_colorbar = False

        if link_cmap is None:
            link_cmap = plt.get_cmap('Spectral_r')
        elif isinstance(link_cmap, list):
            if len(link_cmap) == 1:
                link_cmap = link_cmap*2
            link_cmap = custom_colormap(len(link_cmap), link_cmap)  
            
        link_attribute = _format_link_attribute(link_attribute, wn)
        
        # Replace link_attribute dictionary defined as
        # {link_name: attr} with {(start_node, end_node, link_name): attr}
        attr = {}
        for link_name, value in link_attribute.items():
            link = wn.get_link(link_name)
            attr[(link.start_node_name, link.end_node_name, link_name)] = value
        link_attribute = attr
        
        linklist,linkcolor = zip(*link_attribute.items())
    else:
        linklist = None
        linkcolor = 'k'
    
    if title is not None:
        ax.set_title(title)
        
    edge_background = nx.draw_networkx_edges(G, pos, edge_color='grey', 
                                             width=0.5, ax=ax)
    
    nodes = nx.draw_networkx_nodes(G, pos, 
            nodelist=nodelist, node_color=nodecolor, node_size=node_size, 
            alpha=node_alpha, cmap=node_cmap, vmin=node_range[0], vmax = node_range[1], 
            linewidths=0, ax=ax)
    edges = nx.draw_networkx_edges(G, pos, edgelist=linklist, arrows=directed,
            edge_color=linkcolor, width=link_width, alpha=link_alpha, edge_cmap=link_cmap, 
            edge_vmin=link_range[0], edge_vmax=link_range[1], ax=ax)
    if node_labels:
        labels = dict(zip(wn.node_name_list, wn.node_name_list))
        nx.draw_networkx_labels(G, pos, labels, font_size=7, ax=ax)
    if link_labels:
        labels = {}
        for link_name in wn.link_name_list:
            link = wn.get_link(link_name)
            labels[(link.start_node_name, link.end_node_name)] = link_name
        nx.draw_networkx_edge_labels(G, pos, labels, font_size=7, ax=ax)
    if add_node_colorbar and node_attribute:
        clb = plt.colorbar(nodes, shrink=0.5, pad=0, ax=ax)
        clb.ax.set_title(node_colorbar_label, fontsize=10)
    if add_link_colorbar and link_attribute:
        if link_range[0] is None:
            vmin = min(link_attribute.values())
        else:
            vmin = link_range[0]
        if link_range[1] is None:
            vmax = max(link_attribute.values())
        else:
            vmax = link_range[1]
        sm = plt.cm.ScalarMappable(cmap=link_cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        clb = plt.colorbar(sm, shrink=0.5, pad=0.05, ax=ax)
        clb.ax.set_title(link_colorbar_label, fontsize=10)
        
    ax.axis('off')
    
    if filename:
        plt.savefig(filename)
    
    if show_plot is True:
        plt.show(block=False)
    
    return ax


if __name__ == "__main__":
    unittest.main()
