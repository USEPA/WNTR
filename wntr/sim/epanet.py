from wntr.sim.core import WaterNetworkSimulator
import wntr.epanet.io
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
        if self.reader is None:
            self.reader = wntr.epanet.io.BinFile(result_types=result_types)

    def run_sim(self, file_prefix='temp', save_hyd=False, use_hyd=False, hydfile=None):
        """
        Run the EPANET simulator.

        Runs the EPANET simulator through the compiled toolkit DLL. Can use/save hydraulics
        to allow for separate WQ runs.

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

        """
        inpfile = file_prefix + '.inp'
        self._wn.write_inpfile(inpfile)
        enData = wntr.epanet.toolkit.ENepanet()
        rptfile = file_prefix + '.rpt'
        outfile = file_prefix + '.bin'
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
        return self.reader.read(outfile)

