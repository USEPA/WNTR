from wntr.sim.core import WaterNetworkSimulator
import wntr.epanet.io
from wntr.epanet.util import EN
from wntr.network.base import LinkStatus
import warnings
import logging

logger = logging.getLogger(__name__)

try:
    import wntr.epanet.toolkit
except ImportError as e:
    print('{}'.format(e))
    logger.critical('%s',e)
    raise ImportError('Error importing epanet toolkit while running epanet simulator. '
                      'Make sure libepanet is installed and added to path.')



class EpanetSimulator(WaterNetworkSimulator):
    """
    Fast EPANET simulator class.

    Use the EPANET DLL to run an INP file as-is, and read the results from the
    binary output file. Multiple water quality simulations are still possible
    using the WQ keyword in the run_sim function. Hydraulics will be stored and
    saved to a file. This file will not be deleted by default, nor will any
    binary files be deleted.

    The reason this is considered a "fast" simulator is due to the fact that there
    is no looping within Python. The "ENsolveH" and "ENsolveQ" toolkit
    functions are used instead.


    .. note::

        WNTR now includes access to both the EPANET 2.0.12 and EPANET 2.2 toolkit libraries.
        By default, version 2.2 will be used.


    Parameters
    ----------
    wn : WaterNetworkModel
        Water network model
    reader : wntr.epanet.io.BinFile derived object
        Defaults to None, which will create a new wntr.epanet.io.BinFile object with
        the results_types specified as an init option. Otherwise, a fully
    result_types : dict
        Defaults to None, or all results. Otherwise, is a keyword dictionary to pass to
        the reader to specify what results should be saved.


    .. seealso::

        wntr.epanet.io.BinFile

    """
    def __init__(self, wn, reader=None, result_types=None):
        WaterNetworkSimulator.__init__(self, wn)
        self.reader = reader
        self.prep_time_before_main_loop = 0.0
        self._en = None
        self._t = 0
        if self.reader is None:
            self.reader = wntr.epanet.io.BinFile(result_types=result_types)

    def run_sim(self, file_prefix='temp', save_hyd=False, use_hyd=False, hydfile=None, 
                version=2.2, stop_criteria=None, convergence_error=False):

        """
        Run the EPANET simulator.

        Runs the EPANET simulator through the compiled toolkit DLL. Can use/save hydraulics
        to allow for separate WQ runs. 

        .. note:: 

            By default, WNTR now uses the EPANET 2.2 toolkit as the engine for the EpanetSimulator.
            To force usage of the older EPANET 2.0 toolkit, use the ``version`` command line option.
            Note that if the demand_model option is set to PDD, then a warning will be issued, as
            EPANET 2.0 does not support such analysis.
        

        Parameters
        ----------
        file_prefix : str
            Default prefix is "temp". All files (.inp, .bin/.out, .hyd, .rpt) use this prefix
        use_hyd : bool
            Will load hydraulics from ``file_prefix + '.hyd'`` or from file specified in `hydfile_name`
        save_hyd : bool
            Will save hydraulics to ``file_prefix + '.hyd'`` or to file specified in `hydfile_name`
        hydfile : str
            Optionally specify a filename for the hydraulics file other than the `file_prefix`
        version : float, {2.0, **2.2**}
            Optionally change the version of the EPANET toolkit libraries. Valid choices are
            either 2.2 (the default if no argument provided) or 2.0.
        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False, partial results are returned, 
            a warning will be issued, and results.error_code will be set to 0
            if the simulation does not converge.  Default = False.
        """
        if isinstance(version, str):
            version = float(version)
        inpfile = file_prefix + '.inp'
        self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        rptfile = file_prefix + '.rpt'
        outfile = file_prefix + '.bin'
        
        if (stop_criteria is None) or (stop_criteria.shape[0] == 0):
            stop_criteria_met = True
            if hydfile is None:
                hydfile = file_prefix + '.hyd'
            enData.ENopen(inpfile, rptfile, outfile)
            if use_hyd:
                enData.ENusehydfile(hydfile)
                logger.debug('Loaded hydraulics')
            else:
                enData.ENsolveH()
                logger.debug('Solved hydraulics')
            if save_hyd:
                enData.ENsavehydfile(hydfile)
                logger.debug('Saved hydraulics')
            enData.ENsolveQ()
            logger.debug('Solved quality')
            enData.ENreport()
            logger.debug('Ran quality')
            enData.ENclose()
            logger.debug('Completed run')
            #os.sys.stderr.write('Finished Closing\n')
            # if (stop_criteria is not None) and (stop_criteria.shape[0] != 0):
        else: # Right now this just runs hydraulics
            file_prefix += '_step'
            inpfile = file_prefix + '.inp'
            self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
            enData = wntr.epanet.toolkit.ENepanet(version=version)
            rptfile = file_prefix + '.rpt'
            outfile = file_prefix + '.bin'

            enData.ENopen(inpfile, rptfile, outfile)
            for i in stop_criteria.index:
                link_name = stop_criteria.at[i,'link']
                stop_criteria.loc[i,'_link_index'] = enData.ENgetlinkindex(link_name)
            enData.ENopenH()
            enData.ENinitH(0)
            t = 0
            stop_criteria_met = False
            while True:
                ret = enData.ENrunH()
                for i in stop_criteria.index:
                    link_name, attribute, operation, value, link_index = stop_criteria.loc[i,:]
                    link_attribute = enData.ENgetlinkvalue(int(link_index), int(attribute))
                    if operation(link_attribute, int(value)): # if this isn't status, we should not convert to int
                        stop_criteria_met = True
                        #results.error_code = wntr.sim.results.ResultsStatus.error
                        warnings.warn('Simulation stoped based on stop criteria at time ' + str(t) + '. ') 
                        logger.warning('Simulation stoped based on stop criteria at time ' + str(t) + '. ' ) 
                        break # break out of for loop
                if stop_criteria_met:
                    break # break out of while loop
                
                tstep = enData.ENnextH()
                t = t + tstep
                if (tstep <= 0):
                    continue_sim = False
                    break
            enData.ENcloseH()
            enData.ENclose()

            self._wn.options.time.duration = t
            self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
            enData = wntr.epanet.toolkit.ENepanet(version=version)

            stop_criteria_met = True
            if hydfile is None:
                hydfile = file_prefix + '.hyd'
            enData.ENopen(inpfile, rptfile, outfile)
            if use_hyd:
                enData.ENusehydfile(hydfile)
                logger.debug('Loaded hydraulics')
            else:
                enData.ENsolveH()
                logger.debug('Solved hydraulics')
            if save_hyd:
                enData.ENsavehydfile(hydfile)
                logger.debug('Saved hydraulics')
            enData.ENsolveQ()
            logger.debug('Solved quality')
            enData.ENreport()
            logger.debug('Ran quality')
            enData.ENclose()
            logger.debug('Completed run')

            del stop_criteria['_link_index']
        
        results = self.reader.read(outfile, convergence_error, self._wn.options.hydraulic.headloss=='D-W')
        
        return results

    def _step_get_sensors(self):
        enData = self._en
        if enData is None:
            raise RuntimeError('EpanetSimulator step_sim not initialized before use')
        node_ret = dict()
        link_ret = dict()
        for name, attr, lid, aid in self.__link_sensors:
            value = enData.ENgetlinkvalue(lid, aid)
            if attr not in link_ret:
                link_ret[attr] = dict()
            link_ret[attr][name] = value
        for name, attr, nid, aid in self.__node_sensors:
            value = enData.ENgetnodevalue(nid, aid)
            if attr not in node_ret:
                node_ret[attr] = dict()
            node_ret[attr][name] = value
        return_data = dict(node=node_ret, link=link_ret)
        return return_data

    def step_init(self, file_prefix='temp', save_hyd=False, use_hyd=False, hydfile=None, 
                version=2.2, stop_criteria=None, convergence_error=False, node_sensors=None,
                link_sensors=None):
        file_prefix += '_step'
        inpfile = file_prefix + '.inp'
        self._wn.write_inpfile(inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version)
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        rptfile = file_prefix + '.rpt'
        outfile = file_prefix + '.bin'
        enData.ENopen(inpfile, rptfile, outfile)
        self._en = enData
        enData.ENopenH()
        enData.ENinitH(1)
        # enData.ENinitQ(0)
        enData.ENrunH()
        self._t = 0
        self.__node_sensors = []
        self.__link_sensors = []
        
        logger.debug('Initialized step run')
        
        if link_sensors is not None:
            for name, attr in link_sensors:
                if name == '*':
                    for link_name in self._wn.link_name_list:
                        lid = enData.ENgetlinkindex(link_name)
                        aid = EN[attr.upper()]
                        self.__link_sensors.append((link_name, attr, lid, aid,))
                else:
                    lid = enData.ENgetlinkindex(name)
                    aid = EN[attr.upper()]
                    self.__link_sensors.append((name, attr, lid, aid))
        if node_sensors is not None:
            for name, attr in node_sensors:
                if name == '*':
                    for node_name in self._wn.node_name_list:
                        nid = enData.ENgetnodeindex(node_name)
                        aid = EN[attr.upper()]
                        self.__node_sensors.append((node_name, attr, nid, aid))
                else:
                    nid = enData.ENgetnodeindex(name)
                    aid = EN[attr.upper()]
                    self.__node_sensors.append((name, attr, nid, aid))

        return_data = self._step_get_sensors()
        return self._t, return_data

    def step_sim(self, set_values=None, return_values=None):
        enData = self._en
        if enData is None:
            raise RuntimeError('EpanetSimulator step_sim not initialized before use')

        tstep = enData.ENnextH()
        self._t = self._t + tstep
        if (tstep <= 0):
            self._t = -1
            return self._t, None
        if set_values is not None:
            for name, attr, value in set_values:
                lid = enData.ENgetlinkindex(name)
                if isinstance(attr, (str,)):
                    aid = EN[attr.upper()]
                else:
                    aid = int(attr)
                val = float(value)
                enData.ENsetlinkvalue(lid, aid, val)
        enData.ENrunH()
        logger.debug('Ran 1 step')
        return_data = self._step_get_sensors()
        if set_values is not None:
            for name, attr, value in set_values:
                lid = enData.ENgetlinkindex(name)
                if isinstance(attr, (str,)):
                    aid = EN[attr.upper()]
                else:
                    aid = int(attr)
                val = float(value)
                enData.ENsetlinkvalue(lid, aid, val)
        return self._t, return_data

    def step_kill(self):
        enData = self._en
        if enData is None:
            raise RuntimeError('EpanetSimulator step_sim not initialized before use')
        enData.ENsettimeparam(EN.DURATION, self._t)

    def step_end(self):
        enData = self._en
        if enData is None:
            raise RuntimeError('EpanetSimulator step_sim not initialized before use')
        enData.ENcloseH()
        enData.ENsolveQ()
        logger.debug('Solved quality')
        enData.ENreport()
        logger.debug('Ran quality')
        enData.ENclose()
        logger.debug('Completed step run')