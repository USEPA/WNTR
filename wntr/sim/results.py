"""Simulation results."""

import datetime
import enum


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
        self.link = None
        self.node = None
