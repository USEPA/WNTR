"""
The wntr.stormwater.sim module includes methods to simulate 
hydraulics.
"""
import os
import subprocess
import pyswmm

from wntr.stormwater.io import write_inpfile, read_outfile, read_rptfile

os.environ["CONDA_DLL_SEARCH_MODIFICATION_ENABLE"] = "1"
# See https://github.com/OpenWaterAnalytics/pyswmm/issues/298


class SWMMSimulator(object):
    """
    SWMM simulator class.
    """
    def __init__(self, swn):
        self._swn = swn

    def run_sim(self, file_prefix='temp', return_summary=False):
        """
        Run a SWMM simulation
        
        Parameters
        ----------
        file_prefix : str
            Default prefix is "temp". Output files (.out and .rpt) use this prefix
        return_summary: bool (optional)
            If return_summary is True, the report file is used to 
            extract summary results. If False, the binary output file is used to 
            extract timeseries results. Default = False.
        
        Returns
        -------
        Simulation results from the binary .out file (default) or summary .rpt file
        """
        
        temp_inpfile = file_prefix + '.inp'
        if os.path.isfile(temp_inpfile):
            os.remove(temp_inpfile)
        
        temp_outfile = file_prefix + '.out'
        if os.path.isfile(temp_outfile):
            os.remove(temp_outfile)
        
        temp_rptfile = file_prefix + '.rpt'
        if os.path.isfile(temp_rptfile):
            os.remove(temp_rptfile)

        write_inpfile(self._swn, temp_inpfile)
        
        # The simulation can also be run with pyswmm, see test_stormwater.py, test_basics
        p = subprocess.run("python -m swmmio --run " + temp_inpfile)
        
        # with pyswmm.Simulation(temp_inpfile) as sim: 
        #     for step in sim:
        #         pass
        #     sim.report()
        
        if return_summary:
            results = read_rptfile(temp_rptfile)
        else:
            results = read_outfile(temp_outfile)
            
        return results
