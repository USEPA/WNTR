
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
                wntr.graphics.plot_network(wn, ax=ax[0], title="GIS plot_network", backend='gpd', **kwargs)
                wntr.graphics.plot_network(wn, ax=ax[1], title="NX plot_network", backend='nx', **kwargs)
                fig.savefig(filename, format="png")
                plt.close(fig)
            else:
                wntr.graphics.plot_network(wn, backend='nx', **kwargs)
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
        
        


if __name__ == "__main__":
    unittest.main()
