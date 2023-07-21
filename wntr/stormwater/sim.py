import os
import pyswmm

from wntr.stormwater.io import read_outfile

os.environ["CONDA_DLL_SEARCH_MODIFICATION_ENABLE"] = "1"
# See https://github.com/OpenWaterAnalytics/pyswmm/issues/298


class SWMMSimulator(object):

    def __init__(self, swn):
        self._swn = swn

    def run_sim(self, file_prefix='temp'):

        inpfile = file_prefix + '.inp'
        outfile = file_prefix + '.out'
        
        # Update swmmio model inp based on swn data
        self._swn.udpate_inp_model(inpfile)

        sim = pyswmm.Simulation(inpfile)
        sim.execute()

        results = read_outfile(outfile)

        return results
