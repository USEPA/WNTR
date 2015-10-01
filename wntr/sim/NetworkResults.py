import numpy as np
import datetime
import matplotlib.pylab  as plt

class NetResults(object):
    def __init__(self):
        """
        A class to store water network simulation results.
        """

        # Simulation time series
        self.time = None
        self.generated_datetime = datetime.datetime
        self.network_name = None
        self.simulator_options = {}
        self.solver_statistics = {}
        self.link = None
        self.node = None

    def export_to_csv(self, csv_file_name):
        """
        Write the simulation results to csv file.

        Parameters
        ----------
        csv_file_name : string
            Name of csv file
        """
        # TODO

        pass

    def export_to_yml(self, yml_file_name):
        """
        Write the simulation results to yml file.

        Parameters
        ----------
        yml_file_name : string
            Name of yml file
        """
        # TODO
        pass

    def plot_node_attribute(self, nodes_to_plot=None, param = 'demand', nodeType = None, legend=''):
        nodes = self.node.index.get_level_values('node').drop_duplicates()
        if nodeType is not None:
            nodes = [n for n in nodes if self.node['type'][n][0]==nodeType]
        if nodes_to_plot is not None:
            nodes = set(nodes_to_plot).intersection(nodes)  
        for name in nodes:
            values = [self.node[param][name][t] for t in self.time] 
            plt.plot(self.time,values,label=name+'_'+legend)
        plt.legend()
        plt.xlabel('time')
        plt.ylabel(param)
        plt.title('Node ' +  param)
        #plt.show()

    def plot_link_attribute(self, links_to_plot=None, param = 'flowrate', linkType = None, legend=''):
        links = self.link.index.get_level_values('link').drop_duplicates()
        if linkType is not None:
            links = [n for n in links if self.link['type'][n][0]==linkType]
        if links_to_plot is not None:
            links = set(links_to_plot).intersection(links)  
        for name in links:
            values = [self.link[param][name][t] for t in self.time] 
            plt.plot(self.time,values,label=name+'_'+legend)
        plt.legend()
        plt.xlabel('time')
        plt.ylabel(param)
        plt.title('Link ' +  param)
        #plt.show()



