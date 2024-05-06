"""
The wntr.stormwater.network module includes methods to define
stormwater/wastewater network models.
"""
import logging
import random
import numpy as np
import pandas as pd
import networkx as nx
import warnings
import os

try:
    import swmmio
    has_swmmio = True
except ModuleNotFoundError:
    swmmio = None
    has_swmmio = False

from wntr.stormwater.io import to_graph, to_gis

logger = logging.getLogger(__name__)


class StormWaterNetworkModel(object):
    """
    Storm water network model class.

    Unlike the WaterNetworkModel, this class has no iterator methods,
    add/remove methods, and no component registries.

    Parameters
    -------------------
    inp_file_name: string 
        Directory and filename of SWMM inp file to load into the
        StormWaterNetworkModel object.
    """

    def __init__(self, inp_file_name):
        
        if not has_swmmio:
            raise ModuleNotFoundError('swmmio is required')
        
        from swmmio.defs import INP_OBJECTS
        from swmmio.utils.text import get_inp_sections_details
        import shutil
        
        headers = get_inp_sections_details(inp_file_name, include_brackets=False)
        missing_headers = set(INP_OBJECTS.keys()) - set(headers.keys())
        appended_text = ""
        for missing_header in missing_headers:
            appended_text = appended_text + "[" + missing_header + "]\n\n"
            
        shutil.copyfile(inp_file_name, 'temp.inp')
        with open("temp.inp", "a") as f:
            f.write(appended_text)

        self._swmmio_model = swmmio.Model("temp.inp", include_rpt=False)

        # See https://github.com/pyswmm/swmmio/issues/57 for a list of supported INP file sections
        
        # Attributes of StormWaterNetworkModel link to attributes 
        # in swmmio.Model.inp, which contains dataframes from an INP file.
        # The swmmio.Model.inp object also includes a .save method to 
        # write a new INP file.

        # Nodes = Junctions, outfall, and storage nodes
        # Links = Conduits, weirs, orifices, and pumps
        
        # Sections that are commented out are not currently supported by swntr
        
        self.section_names = [
            # Options
            'options',
            'report',
            'files', 
            
            # Climate
            'raingages',
            'evaporation',
            'subcatchments', 
            'subareas',
            'infiltration',
            
            # Hydraulics
            'junctions',
            'outfalls',
            'storage',
            'conduits',
            'pumps',
            'orifices',
            'weirs',
            'xsections', # requires udpate to swmmio
            'streets',
            'inlets',
            'inlet_usage',
            'controls', # requires udpate to swmmio
            
            # Quality
            'pollutants',
            'landuses',
            'coverages',
            'buildup',
            'washoff',
            'inflows', # requires udpate to swmmio
            'dwf',
            
            # Curves, timeseries, patterns
            'curves', # requires udpate to swmmio
            'timeseries',
            'patterns', # requires udpate to swmmio
            
            # Map
            'polygons',
            'coordinates',
            'vertices',
            'tags',
            
            # Not included or empty in INP test files (see "untested" in tests)
            'hydrographs', 
            'loadings', 
            'groundwater', 
            'aquifers', 
            'losses', 
            'dividers', 
            'lid_usage', 
            'rdii',

            # Not supported by swmmio model.inp
            #'title',
            #'temperature',
            #'adjustments',
            #'lid_controls',
            #'gwf', 
            #'snowpacks',
            #'outlets',
            #'transects',
            #'treatment', 
            #'map',
            #'labels',
            #'symbols',
            #'backdrop',
            ]
        for sec in self.section_names:
            df = getattr(self._swmmio_model.inp, sec)
            setattr(self, sec, df.copy())
            
        # Reset inp file path and remove temp file
        self._swmmio_model.inp.path = inp_file_name
        os.remove("temp.inp")
        
    def describe(self):
        """
        Describe number of components in the network model
        
        Returns
        -------
        A pandas Series with component counts
        """
        d = {}
        for sec in self.section_names:
            df = getattr(self, sec)
            d[sec] = df.shape[0]

        return pd.Series(d)
    
    @property
    def nodes(self):
        """Nodes database (read only)"""
        return pd.concat([self.junctions, 
                          self.outfalls,
                          self.storage])
    
    @property
    def links(self):
        """Links database (read only)"""
        return pd.concat([self.conduits, 
                          self.weirs,
                          self.orifices,
                          self.pumps])

    @property
    def node_name_list(self):
        """List of node names"""
        return list(self.nodes.index)

    @property
    def junction_name_list(self):
        """List of junction names"""
        return list(self.junctions.index)

    @property
    def outfall_name_list(self):
        """List of outfall names"""
        return list(self.outfalls.index)

    @property
    def storage_name_list(self):
        """List of storage names"""
        return list(self.storage.index)

    @property
    def link_name_list(self):
        """List of link names"""
        return list(self.links.index)

    @property
    def conduit_name_list(self):
        """List of conduit names"""
        return list(self.conduits.index)

    @property
    def weir_name_list(self):
        """List of weir names"""
        return list(self.weirs.index)

    @property
    def orifice_name_list(self):
        """List of orifice names"""
        return list(self.orifices.index)

    @property
    def pump_name_list(self):
        """List of pump names"""
        return list(self.pumps.index)

    @property
    def subcatchment_name_list(self):
        """List of subcatchment names"""
        return list(self.subcatchments.index)

    @property
    def raingage_name_list(self):
        """List of raingage names"""
        return list(self.raingages.index)
    
    @property
    def timeseries_name_list(self):
        """List of timeseries names"""
        return list(self.timeseries.index.unique())
    
    @property
    def controls_name_list(self):
        """List of control names"""
        return list(self.controls.index)

    # @property
    # def num_nodes(self):
    #     """Number of nodes"""
    #     return len(self.node_name_list)

    # @property
    # def num_junctions(self):
    #     """Number of junctions"""
    #     return len(self.junction_name_list)

    # @property
    # def num_outfalls(self):
    #     """Number of outfalls"""
    #     return len(self.outfall_name_list)

    # @property
    # def num_storages(self):
    #     """Number of storages"""
    #     return len(self.storage_name_list)

    # @property
    # def num_links(self):
    #     """Number of links"""
    #     return len(self.link_name_list)

    # @property
    # def num_conduits(self):
    #     """Number of conduits"""
    #     return len(self.conduit_name_list)

    # @property
    # def num_weirs(self):
    #     """Number of weirs"""
    #     return len(self.weir_name_list)

    # @property
    # def num_orifices(self):
    #     """Number of orifices"""
    #     return len(self.orifice_name_list)

    # @property
    # def num_pumps(self):
    #     """Number of pumps"""
    #     return len(self.pump_name_list)

    # @property
    # def num_subcatchments(self):
    #     """Number of subcatchments"""
    #     return len(self.subcatchment_name_list)

    # @property
    # def num_raingages(self):
    #     """Number of raingages"""
    #     return len(self.raingage_name_list)

    def get_node(self, name):
        """Get a specific node

        Parameters
        ----------
        name : str
            The node name

        Returns
        -------
        Node

        """
        return Node(name, self.nodes.loc[name,:])

    def get_link(self, name):
        """Get a specific link

        Parameters
        ----------
        name : str
            The link name

        Returns
        -------
        Link

        """
        return Link(name, self.links.loc[name,:])
    
    @property
    def conduit_cross_section(self):
        """
        Cross section area of each conduit, according to the geometric 
        parameters stored in xsections
        """

        cross_section = {}

        for link_name in self.conduit_name_list:

            geom1 = self.xsections.loc[link_name, 'Geom1']
            geom2 = self.xsections.loc[link_name, 'Geom2']
            geom3 = self.xsections.loc[link_name, 'Geom3']
            geom4 = self.xsections.loc[link_name, 'Geom4']
            shape = self.xsections.loc[link_name, 'Shape']

            if shape == "CIRCULAR":
                d = geom1 # diameter
                r = d/2 # radius

                area = np.pi*(r**2)

            elif shape == "FILLED_CIRCULAR":
                d = geom1 # diameter
                r = d/2 # radius
                h = geom2 # height
                
                circular_area = np.pi*(r**2)
                filled_area = 0.5*(r**2)*(2*np.arccos((r-h)/r))-np.sin((2*np.arccos((r-h)/r)))
                area = circular_area - filled_area

            elif shape == "RECT_CLOSED":
                h = geom1 # height
                b = geom2 # base (width)
                
                area = h*b

            elif shape == "RECT_OPEN":
                h = geom1 # height
                b = geom2 # base (width)
                
                area = h*b

            elif shape == "TRAPEZOIDAL":
                h = geom1 # height
                b = geom2 # width
                p1 = geom3 # pitch, side 1
                p2 = geom4 # pitch, side 2
                
                area = 0.5*h*(h + (b + np.sqrt((p1**2) - h**2) + np.sqrt((p2**2) - h**2))) 

            elif shape == "TRIANGULAR":
                area = (0.5*geom1*geom2)

            elif shape == "HORIZ_ELLIPSE":
                area = np.pi*(geom1*0.5)*(geom2*0.5)

            elif shape == "VERT_ELLIPSE":
                area = np.pi*(geom1*0.5)*(geom2*0.5)

            elif shape == "PARABOLIC":
                area = (2/3)*geom1*geom2

            elif shape == "RECT_TRIANGULAR":
                area = (geom1*geom2)+(0.5*geom3*geom2)
                                  
            else: # ARCH, POWER, CUSTOM
                area = None
                warnings.warn(shape + ' not yet implemented')

            cross_section[link_name] = area
            
        return pd.Series(cross_section)
    
    @property
    def conduit_volume(self):
        """
        Volume of each conduit, according to the geometric 
        parameters stored in xsections and length
        """
        
        cross_section = self.conduit_cross_section
        length =self.conduits['Length']
        volume = cross_section*length
        
        return volume
        
    def anonymize_coordinates(self, seed=None, update_model=True):
        
        G = self.to_graph()

        pos = nx.spring_layout(G, seed=seed)
        coordinates = pd.DataFrame(pos).T
        coordinates.rename(columns={0: 'X', 1: 'Y'}, inplace=True)
        
        if update_model:
            self.coordinates = coordinates
            self.vertices.drop(self.vertices.index, inplace=True)
            self.polygons.drop(self.polygons.index, inplace=True)
            
        return coordinates
        
    def patterns_to_datetime_format(self):
        pass
    
    def patterns_from_datetime_format(self):
        pass
    
    def timeseries_to_datetime_format(self):
        """
        Reformat "Date, Time, Value" timeseries to a datetime indexed DataFrame

        Returns
        -------
        pandas DataFrame, with one column per named timeseries

        """
        assert set(self.timeseries.columns) == set(['Date', 'Time', 'Value'])
        
        start_date_value = self.options.loc['START_DATE','Value']
            
        ts = {}
        for name, timeseries in self.timeseries.groupby('Name'):
            timeseries.loc[timeseries['Date'].isna(), 'Date'] = start_date_value
            datestr = timeseries['Date'] + ' ' + timeseries['Time']
            datetime = pd.DatetimeIndex(datestr)
            value = timeseries['Value'].astype(float).values
            ts[name] = pd.Series(data=value, index=datetime)

        ts = pd.DataFrame(ts)
        
        return ts
    
    def add_timeseries_from_datetime_format(self, ts, name=None, update_model=True):
        
        if name is None:
            name = ts.name
        ts = ts.to_frame(name)
        timeseries = ts.unstack().reset_index()
        timeseries = timeseries.set_index('level_1')
        timeseries['Date'] = timeseries.index.strftime('%m/%d/%Y')
        timeseries['Time'] = timeseries.index.strftime('%H:%M')
        timeseries = timeseries.set_index('level_0')
        timeseries.index.name = 'Name'
        timeseries.rename(columns={0: 'Value'}, inplace=True)
        timeseries = timeseries[['Date', 'Time', 'Value']]
        
        if update_model:
            self.timeseries = pd.concat([self.timeseries, timeseries], axis=0)
            
        return timeseries
        
    def to_gis(self, crs=None):
        """
        Convert a StormWaterNetworkModel into GeoDataFrames

        Parameters
        ----------
        crs : str, optional
            Coordinate reference system, by default None
        """
        return to_gis(self, crs)

    def to_graph(self, node_weight=None, link_weight=None, modify_direction=False):
        """
        Convert a StormWaterNetworkModel into a networkx MultiDiGraph

        Returns
        --------
        networkx MultiDiGraph
        """
        return to_graph(self, node_weight, link_weight, modify_direction)

    def add_pump_outage_control(self, pump_name, start_time, end_time=None, 
                                priority=4, control_suffix="_outage", 
                                update_model=True):
        """
        Add a pump outage rule to the stormwater network model.
    
        Parameters
        ----------
        start_time : int
           The time at which the outage starts in decimal hours
        end_time : int
           The time at which the outage stops in decimal hours
        priority : int
            The outage rule priority, default = 4 (highest priority)
        """
        assert pump_name in self.pump_name_list
        
        rule_name = 'RULE ' + pump_name + control_suffix
        
        rule = "IF SIMULATION TIME > " + str(start_time) + " "
        if end_time is not None:
            rule = rule + "AND SIMULATION TIME < "+str(end_time) + " "
        rule = rule + "THEN PUMP "+pump_name+" status = OFF " 
        rule = rule + "ELSE PUMP "+pump_name+" status = ON "
        rule = rule + "PRIORITY "+str(priority)
        
        if update_model:
            self.controls.loc[rule_name, 'Control'] = rule
        
        return rule
        
    def add_composite_patterns(self, data, pattern_suffix="_Composite", 
                               update_model=True):
        """
        Add composite dry weather flow (DWF) and composite patterns to the 
        model, computed from data that contains multiple base values and 
        pattern names per node.  

        Composite DWFs override existing DWF (see `swn.dwf`).  

        Composite pattern values (Factor1, Factor2, ...)
        have a mean value of 1 and are appended to existing patterns.  Patterns
        are named <node name> + pattern_suffix (see `swn.patterns`). 

        Parameters
        ----------
        data : pd.DataFrame
            Data containing multiple base and pattern names per node.
            DataFrame columns = ['Node', 'Base', 'Pattern'] where 
            the Node column contains node names, 
            the Base column contains base values for mean flow, and 
            the Pattern column contains pattern names that already exist in the 
            model (swn).

        pattern_suffix : string (optional, default = "_Composite")
            Pattern name suffix, appended to the node name

        add_to_model : Bool (optional, default = True)
            Flag indicating if the composite DWF and Patterns are added to the
            model. If False, the composite base and patterns are returned, but 
            not used to update the model (swn).

        Returns
        -------
        pd.DataFrame with one base and pattern value per node.
        """

        mask = self.patterns.columns.str.contains('Factor')
        factor_cols = self.patterns.columns[mask]

        assert self.patterns.loc[:,factor_cols].isna().sum().sum() == 0, \
            "Composite patterns is not implemented for variable pattern length"

        nodes = data.index.unique()
        cols = ['Base']
        cols.extend(list(factor_cols))
        composite = pd.DataFrame(index=nodes, columns=cols)

        for name, group in data.groupby('Node'):
            patterns = group['Pattern']

            factors = self.patterns.loc[patterns, factor_cols].values
            base = group['Base'].values
            scaled = np.multiply(factors, np.expand_dims(base, axis=1))
            composite_vals = scaled.sum(axis=0)

            composite_base = np.round(composite_vals.mean(), 6)
            composite_factors = composite_vals
            if composite_base > 0:
                composite_factors = composite_factors/composite_base
            composite_factors = np.around(composite_factors, 6)

            composite.loc[name, 'Base'] = composite_base
            composite.loc[name, factor_cols] = composite_factors

        data = composite.copy()
        data['TimePatterns'] = data.index + pattern_suffix

        composite_dwf = data[['Base', 'TimePatterns']]
        composite_dwf.loc[:,'Parameter'] = 'FLOW'
        composite_dwf.rename(columns={'Base':'AverageValue'}, inplace=True)
        composite_dwf = composite_dwf[['Parameter', 'AverageValue', 'TimePatterns']]

        composite_patterns = data[factor_cols]
        composite_patterns.index = data['TimePatterns']
        composite_patterns.loc[:, 'Type'] = 'HOURLY'

        if update_model:
            # Override DWF with new composite values
            self.dwf.loc[composite_dwf.index, :] = composite_dwf

            # Concat Patterns with new composite values
            concat_patterns = pd.concat([self.patterns, composite_patterns])
            self.patterns = concat_patterns

        return composite

class Node(object):
    """
    Base class for nodes.
    """

    def __init__(self, name, data):

        # Set the node name
        self._name = name

    @property
    def name(self):
        """str: The name of the node (read only)"""
        return self._name


class Link(object):
    """
    Base class for links.
    """

    def __init__(self, name, data):

        self._link_name = name
        self._start_node_name = data['InletNode']
        self._end_node_name = data['OutletNode']

    @property
    def name(self):
        """str: The link name (read only)"""
        return self._link_name

    @property
    def start_node_name(self):
        """str: The name of the start node (read only)"""
        return self._start_node_name

    @property
    def end_node_name(self):
        """str: The name of the end node (read only)"""
        return self._end_node_name


def generate_valve_layer(swn, placement_type='strategic', n=1, seed=None):
    """
    Generate valve layer data, which can be used in valve segmentation analysis.

    Parameters
    -----------
    swn : wntr StrormWaterNetworkModel
        A StormWaterNetworkModel object
        
    placement_type : string
        Options include 'strategic' and 'random'.  
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve. In this case, n is generally 0, 1 or 2 
          (i.e. N, N-1, N-2 valve placement).
        - If 'random', then n randomly placed valves are used to define the 
          valve layer.
        
    n : int
        
        - If 'strategic', n is the number of pipes from each node that do not 
          contain a valve.
        - If 'random', n is the number of number of randomly placed valves.
        
    seed : int or None
        Random seed
       
    Returns
    ---------
    valve_layer : pandas DataFrame
        Valve layer, defined by node and link pairs (for example, valve 0 is 
        on link A and protects node B). The valve_layer DataFrame is indexed by
        valve number, with columns named 'node' and 'link'.
    """
    
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    valve_layer = []
    if placement_type=='random':
        s = swn.conduits['InletNode']
        all_valves = list(tuple(zip(s.index,s)))
        s = swn.conduits['OutletNode']
        all_valves.extend(tuple(zip(s.index,s)))
        for valve_tuple in random.sample(all_valves, n):
            pipe_name, node_name = valve_tuple
            valve_layer.append([pipe_name, node_name])
            
    elif placement_type == 'strategic':
        s = pd.concat([swn.conduits['InletNode'], swn.conduits['OutletNode']])
        s = s.to_frame('Node')
        for node_name, group in s.groupby('Node'):
            links = list(group.index)
            for l in np.random.choice(links, max(len(links)-n,0), replace=False):
                valve_layer.append([l, node_name])
            
    valve_layer = pd.DataFrame(valve_layer, columns=['link', 'node'])  
    
    return valve_layer
