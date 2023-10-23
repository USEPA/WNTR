import os
import pyswmm

from wntr.stormwater.io import write_inpfile, read_outfile

os.environ["CONDA_DLL_SEARCH_MODIFICATION_ENABLE"] = "1"
# See https://github.com/OpenWaterAnalytics/pyswmm/issues/298


class SWMMSimulator(object):
    """
    SWMM simulator class.
    """
    def __init__(self, swn):
        self._swn = swn

    def run_sim(self, file_prefix='temp'):
        """Run a SWMM simulation"""
        inpfile = file_prefix + '.inp'
        if os.path.isfile(inpfile):
            os.remove(inpfile)
        
        outfile = file_prefix + '.out'
        if os.path.isfile(outfile):
            os.remove(outfile)

        write_inpfile(self._swn, inpfile)

        # The use of swmmio run command seems slower 
        # import subprocess
        # subprocess.run("python -m swmmio --run " + inpfile)

        # The use of pyswmm has compatibility issues with some inp files
        with pyswmm.Simulation(inpfile) as sim: 
            for step in sim:
                pass
            sim.report()

        results = read_outfile(outfile)

        return results
