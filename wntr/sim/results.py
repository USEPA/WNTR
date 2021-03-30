import datetime
import enum
import copy
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam
from wntr.epanet.util import from_si

class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0


class SimulationResults(object):
    """
    Water network simulation results class.
    """

    def __init__(self):

        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        self.sim_time = 0
        self.link = None
        self.node = None

    def convert_units(self, flow_units='GPM', mass_units='mg', qual_param=None, 
                      return_copy=True):
        """
        Convert simulation results to EPANET unit convensions.
        
        See https://wntr.readthedocs.io/en/stable/units.html#epanet-unit-conventions for more details.
        
        Parameters
        ------------
        flow_units : str
            Flow unit used for conversion.  For example, GPM or LPS.
            flow_unit must be defined in wntr.epanet.util.FlowUnits
            
        mass_units : str
            Mass unit unsed for conversion.  For example, mg or g.
            mass_unit must be defined in wntr.epanet.util.MassUnits
            
        qual_param : str
            Quality parameter used for conversion, generally taken from wn.options.quality.parameter,
            Options include CONCENTRATION, AGE, TRACE or None.
            If qual_param is TRACE or None, no conversion is needed (unitless).
            
        """
        if return_copy:
            results = copy.deepcopy(self)
        else:
            results = self
            
        if flow_units is not None and isinstance(flow_units, str):
            flow_units = flow_units.upper()
            flow_units = FlowUnits[flow_units]
            
        if mass_units is not None and isinstance(mass_units, str):
            mass_units = mass_units.lower()
            mass_units = MassUnits[mass_units]
        
        if qual_param is not None and isinstance(qual_param, str) and qual_param in ['CONCENTRATION', 'AGE', 'TRACE', 'NONE']:
            qual_param = qual_param.upper()
            #qual_param = QualParam[qual_param]
        
        ## Nodes ##
        for key in results.node.keys():
            results.node[key].index = results.node[key].index/3600
        
        results.node['demand'] = from_si(flow_units, results.node['demand'], HydParam.Demand)
        results.node['head'] = from_si(flow_units, results.node['head'], HydParam.HydraulicHead)
        results.node['pressure'] = from_si(flow_units, results.node['pressure'], HydParam.Pressure)
        
        if qual_param == 'CHEMICAL':
            results.node['quality'] = from_si(flow_units, results.node['quality'], QualParam.Concentration, mass_units=mass_units)
        elif qual_param == 'AGE':
            results.node['quality']  = from_si(flow_units, results.node['quality'], QualParam.WaterAge)
        else:
            pass # Trace or None, no conversion needed
        
        ## Links ##
        for key in self.link.keys():
            results.link[key].index = results.link[key].index/3600
    
        results.link['flowrate'] = from_si(flow_units, results.link['flowrate'], HydParam.Flow)
        results.link['headloss'] = from_si(flow_units, results.link['headloss'], HydParam.HeadLoss)
        results.link['velocity'] = from_si(flow_units, results.link['velocity'], HydParam.Velocity)
        
        if qual_param == 'CHEMICAL':
            results.link['linkquality']  = from_si(flow_units, results.link['linkquality'], QualParam.Concentration, mass_units=mass_units)
        elif qual_param == 'AGE':
            results.link['linkquality']  = from_si(flow_units, results.link['linkquality'], QualParam.WaterAge)
        else:
            pass # Trace or None, no conversion needed
        
        # frictionfact no conversion needed
        # status no conversion needed
        # setting requires valve type, convert with pressure or flow type, or change setting to pressure_setting and flow_setting.
        # rxnrate, convert with BulkReactionCoeff? or WallReactionCoeff?
        
        return results