import numpy as np
from networkx.classes.multidigraph import MultiDiGraph

class WDSGraph(MultiDiGraph):
        
    def get_edge_attributes(self, attribute):
        """ Adaptation of nx.get_edge_attributes, includes edge key
        
        Returns 
        -------
        returns {(u,v,k): value} instead of {(u,v): value}
        
        """
        edge_attribute = dict()
        for u,v,k,d in self.edges(keys=True,data=True):
            if attribute in d:
                edge_attribute[(u,v,k)] = d[attribute] 
           
           
        return edge_attribute
       
    def query_node_attribute(self, attribute, operation, value):
        """ Query node attributes, for example get all nodes with elevation <= treshold
            
        Parameters
        ----------
        G : graph
            A networkx graph
        
        attribute: string
            Pipe attribute
            
        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal    
            
        value: scalar
            treshold
            
        Returns
        -------
        pipes : list
            list of nodeid
            
        Examples
        --------
        >>> nzd_nodes = query_node_attribute(G, 'base_demand', np.greater, 0)
        """
        
        
        """
        attr = nx.get_node_attributes(self, attribute)
        condition = operation(attr.values(),value)
        node_names = np.array(attr.keys()) 
        node = list(node_names[condition])
        """
        
        nodes = []
        for i in self.nodes():
            node_attribute = self.node[i][attribute]
            if not np.isnan(node_attribute):
                if operation(node_attribute, value):
                    nodes.append(i)
                
        return nodes

    def query_pipe_attribute(self,attribute, operation, value):
        """ Query pipe attributes, for example get all pipe diameters > treshold
            
        Parameters
        ----------
        G : graph
            A networkx graph
        
        attribute: string
            Pipe attribute
            
        operation: np option
            options = np.greater, np.greater_equal, np.less, np.less_equal, np.equal, np.not_equal    
            
        value: scalar
            treshold
            
        Returns
        -------
        pipes : list
            list of tuples (node1, node2, linkid)
        """
        pipes = []
        for i,j,k in self.edges(keys=True):
            pipe_attribute = self.edge[i][j][k][attribute]
            if not np.isnan(pipe_attribute):
                if operation(pipe_attribute, value):
                    pipes.append((i,j,k))
                
        return pipes