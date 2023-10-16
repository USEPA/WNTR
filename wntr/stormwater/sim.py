import os
import pyswmm

from wntr.stormwater.io import write_inpfile, read_outfile

os.environ["CONDA_DLL_SEARCH_MODIFICATION_ENABLE"] = "1"
# See https://github.com/OpenWaterAnalytics/pyswmm/issues/298


class SWMMSimulator(object):

    def __init__(self, swn):
        self._swn = swn

    def run_sim(self, file_prefix='temp'):

        inpfile = file_prefix + '.inp'
        outfile = file_prefix + '.out'

        write_inpfile(self._swn, inpfile)

        # The use of swmmio run command seems slower and would not report errors
        # import subprocess
        # subprocess.run("python -m swmmio --run " + inpfile)

        with pyswmm.Simulation(inpfile) as sim: 
            for step in sim:
                pass
            sim.report()

        results = read_outfile(outfile)

        return results
