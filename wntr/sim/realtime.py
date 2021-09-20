from abc import abstractmethod
from wntr.sim.core import WaterNetworkSimulator
import wntr.epanet.io
from wntr.epanet.util import EN
from wntr.network.base import LinkStatus
import warnings
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import wntr.epanet.toolkit
except ImportError as e:
    print("{}".format(e))
    logger.critical("%s", e)
    raise ImportError(
        "Error importing epanet toolkit while running epanet simulator. "
        "Make sure libepanet is installed and added to path."
    )


class RealtimeProvider:
    def __init__(self, timelimit=86400, outfile="sensors.out", infile="controls.in", controls=None):
        self._timelimit = timelimit
        self._outfile = outfile
        self._infile = infile
        self._controls = controls
        with open(self._outfile, "w") as out:
            out.write("# time, sensor, value\n")
        self._data = dict()
        with open(self._infile, "r") as inf:
            for line in inf.readlines():
                if line.startswith("#"):
                    continue
                try:
                    t, k, v = line.strip().split(",")
                    if int(t) not in self._data.keys():
                        self._data[int(t)] = dict()
                    self._data[int(t)][k] = float(v)
                except:
                    continue
        self._current = dict()

    def proc_sensors(self, t: int, values: dict):
        with open(self._outfile, "a") as out:
            for k, v in values.items():
                out.write("{},{},{}\n".format(t,k,v))
                self._current[k] = v

    def proc_controllers(self, t: int) -> dict:
        values = dict()
        inctrl = self._data.setdefault(t, None)
        if isinstance(inctrl, (dict,)):
            for k, v in inctrl.items():
                values[k] = v
        if self._controls is not None:
            for control in self._controls:
                if control[1](self._current[control[0]], control[2]):
                    values[control[3]] = control[4]
        return values

    def check_time(self, t) -> bool:
        return True if t >= self._timelimit else False


class StepwiseSimulator(WaterNetworkSimulator):
    @abstractmethod
    def initialize(self, transmit, receive, stop, **kwargs):
        """
        [summary]

        Parameters
        ----------
        transmit : function
            a function that accepts an integer time and a dictionary 
            of sensor IDs and values
        receive : function
            a function that accepts an integer time returns and a dictionary 
            of controller IDs and values
        stop : function
            a function that accepts an integer of the current time and returns 
            a boolean indicating whether to stop the simulation
        **kwargs
            other keyword arguments that are passed to the simulator
        """
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def add_sensor_instrument(self):
        pass

    @abstractmethod
    def add_controller_instrument(self):
        pass

    @abstractmethod
    def get_sensor_values(self):
        pass


class EpanetStepwiseSimulator(StepwiseSimulator):
    """
    A real-time simulator to provide a system model for use with other models.

    Unlike the other WaterNetworkSimulator classes, the LoopedSimulator requires 
    an additional configuration 

    """

    def __init__(self, wn):
        WaterNetworkSimulator.__init__(self, wn)
        self.prep_time_before_main_loop = 0.0
        self._en = None
        self._t = 0
        self.sensors = dict()
        self.controllers = dict()
        self.__node_sensors = list()
        self.__link_sensors = list()
        self.__link_setters = dict()
        self.transmit = None
        self.receive = None
        self.stop = None

    def add_sensor_instrument(
        self, name: str, wn_type: str, wn_name: str, attribute: str,
    ):
        """
        Add a read-only sensor instrument to the simulator.

        Instrument names must be unique across both read-only and read-write
        instruments. Read-only instruments are sensors which return values 
        to the outside observer. 

        Parameters
        ----------
        name : str
            a unique name for the instrument
        wn_type : {'node', 'link', ...}
            any of 'node', 'link', 'junction', 'tank', ...
        wn_name : str
            name of the node or link within the wn
        attribute : str
            the attribute name (or wntr.epanet.util.EN enum value) 
            for the attribute to be read
        """
        self.sensors[name] = (wn_type, wn_name, attribute)

    def add_controller_instrument(
        self, name: str, wn_name: str, attribute: str,
    ):
        """
        Add a read-write instrument to the system.

        Instrument names must be unique across both read-only and read-write
        instruments. Read-write instruments are combined sensors/controllers 
        which both return values to the outside and allow the outside to set
        values on statuses and settings.

        Controllers can only be added to pipes, pumps, and valves.
        It is assumed that controllers will output their status along with 
        sensors at every timestep, as it is important for a control system
        to know whether a command has been obeyed.

        Parameters
        ----------
        name : str
            unique name for the instrument
        wn_name : str
            name of the link within the wn model
        attribute : str
            name of the attribute to read and change
        """
        self.sensors[name] = ("link", wn_name, attribute)
        self.controllers[name] = (wn_name, attribute)

    def set_sensor_values(self, values: dict):
        enData = self._en
        if enData is None:
            raise RuntimeError("StepwiseSimulator not initialized before use")
        for name, value in values.items():
            if name in self.__link_setters.keys():
                sensname, wn_name, attr, lid, aid = self.__link_setters[name]
                enData.ENsetlinkvalue(lid, aid, value)

    def get_sensor_values(self) -> dict:
        enData = self._en
        if enData is None:
            raise RuntimeError("StepwiseSimulator not initialized before use")
        values = dict()
        for sensname, name, attr, lid, aid in self.__link_sensors:
            value = enData.ENgetlinkvalue(lid, aid)
            values[sensname] = value
        for sensname, name, attr, nid, aid in self.__node_sensors:
            value = enData.ENgetnodevalue(nid, aid)
            values[sensname] = value
        return values

    def initialize(
        self,
        transmit,
        receive,
        stop,
        file_prefix: str = "temp",
        version=2.2,
        save_hyd=False,
        use_hyd=False,
        hydfile=None,
    ):
        self.transmit = transmit
        self.receive = receive
        self.stop = stop
        inpfile = file_prefix + ".inp"
        enData = wntr.epanet.toolkit.ENepanet(version=version)
        self._wn.write_inpfile(
            inpfile, units=self._wn.options.hydraulic.inpfile_units, version=version
        )
        rptfile = file_prefix + ".rpt"
        outfile = file_prefix + ".bin"
        self.outfile = outfile
        enData.ENopen(inpfile, rptfile, outfile)
        self._en = enData
        enData.ENopenH()
        enData.ENinitH(1)
        enData.ENopenQ()
        enData.ENinitQ(1)
        enData.ENrunH()
        enData.ENrunQ()
        self._t = 0

        logger.debug("Initialized realtime run")

        for name, vals in self.sensors.items():
            wn_type, wn_name, attr = vals
            if wn_type.lower() in ["node", "junction", "tank", "reservoir"]:
                nid = enData.ENgetnodeindex(wn_name)
                aid = EN[attr.upper()]
                self.__node_sensors.append((name, wn_name, attr, nid, aid))
            elif wn_type.lower() in ["link", "pump", "pipe", "valve"]:
                lid = enData.ENgetlinkindex(wn_name)
                aid = EN[attr.upper()]
                self.__link_sensors.append((name, wn_name, attr, lid, aid))
        for name, vals in self.controllers.items():
            wn_name, attr = vals
            lid = enData.ENgetlinkindex(wn_name)
            aid = EN[attr.upper()]
            self.__link_setters[name] = (name, wn_name, attr, lid, aid)

        values = self.get_sensor_values()
        self.transmit(self._t, values)
        values = self.receive(self._t)
        self.set_sensor_values(values)
        tstep = enData.ENnextH()
        qstep = enData.ENnextQ()
        self._t = self._t + tstep

    def run_sim(self, until=np.inf):
        enData = self._en
        if enData is None:
            raise RuntimeError("EpanetSimulator step_sim not initialized before use")

        while True:
            # values = self.get_sensor_values()
            # self.transmit(self._t, values)
            values = self.receive(self._t)
            self.set_sensor_values(values)
            enData.ENrunH()
            enData.ENrunQ()
            values = self.get_sensor_values()
            self.transmit(self._t, values)
            # values = self.receive(self._t)
            # self.set_sensor_values(values)
            logger.debug("Ran 1 step")
            if self._t >= until or self.stop(self._t):
                enData.ENsettimeparam(EN.DURATION, self._t)
            tstep = enData.ENnextH()
            qstep = enData.ENnextQ()
            if tstep <= 0:
                self._t = 0
                break
            self._t = self._t + tstep

    def close(self):
        enData = self._en
        if enData is None:
            raise RuntimeError("EpanetSimulator step_sim not initialized before use")
        enData.ENcloseH()
        enData.ENcloseQ()
        logger.debug("Solved quality")
        enData.ENreport()
        logger.debug("Ran quality")
        enData.ENclose()
        logger.debug("Completed step run")
        results = wntr.epanet.io.BinFile().read(self.outfile)
        return results
