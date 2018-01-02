"""
The wntr.network.controls module includes methods to define network controls
and control actions.  These controls modify parameters in the network during
simulation.
"""
import wntr
import math
import enum
import numpy as np
import logging
import six
from .elements import LinkStatus
import abc
from wntr.utils.ordered_set import OrderedSet
from collections import OrderedDict, Iterable
import warnings

logger = logging.getLogger(__name__)

# Control Priorities:
# 0 is the lowest
# 3 is the highest
#
# 0:
#    Open check valves/pumps if flow would be forward
#    Open links for time controls
#    Open links for conditional controls
#    Open links connected to tanks if the tank head is larger than the minimum head plus a tolerance
#    Open links connected to tanks if the tank head is smaller than the maximum head minus a tolerance
#    Open pumps if power comes back up
#    Start/stop leaks
# 1:
#    Close links connected to tanks if the tank head is less than the minimum head (except check valves and pumps than
#    only allow flow in).
#    Close links connected to tanks if the tank head is larger than the maximum head (exept check valves and pumps that
#    only allow flow out).
# 2:
#    Open links connected to tanks if the level is low but flow would be in
#    Open links connected to tanks if the level is high but flow would be out
#    Close links connected to tanks if the level is low and flow would be out
#    Close links connected to tanks if the level is high and flow would be in
# 3:
#    Close links for time controls
#    Close links for conditional controls
#    Close check valves/pumps for negative flow
#    Close pumps without power


class Subject(object):
    """
    A subject base class for the observer design pattern
    """
    def __init__(self):
        self._observers = OrderedSet()

    def subscribe(self, observer):
        self._observers.add(observer)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for o in self._observers:
            o.update(self)


class Observer(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def update(self, subject):
        pass


class Comparison(enum.Enum):
    gt = (1, np.greater)
    ge = (2, np.greater_equal)
    lt = (3, np.less)
    le = (4, np.less_equal)
    eq = (5, np.equal)
    ne = (6, np.not_equal)

    def __str__(self):
        return '-' + self.name

    @property
    def func(self):
        """The function call to use for this comparison"""
        return self.value[1]
    __call__ = func

    @property
    def symbol(self):
        if self is Comparison.eq:
            return '='
        elif self is Comparison.ne:
            return '<>'
        elif self is Comparison.gt:
            return '>'
        elif self is Comparison.ge:
            return '>='
        elif self is Comparison.lt:
            return '<'
        elif self is Comparison.le:
            return '<='
        raise ValueError('Unknown Enum: Comparison.%s'%self)

    @property
    def text(self):
        if self is Comparison.eq:
            return 'Is'
        elif self is Comparison.ne:
            return 'Not'
        elif self is Comparison.gt:
            return 'Above'
        elif self is Comparison.ge:
            return '>='
        elif self is Comparison.lt:
            return 'Below'
        elif self is Comparison.le:
            return '<='
        raise ValueError('Unknown Enum: Comparison.%s'%self)

    @classmethod
    def parse(cls, func):
        if isinstance(func, six.string_types):
            func = func.lower().strip()
        if func in [np.equal, '=', 'eq', '-eq', '==', 'is', 'equal', 'equal to']:
            return cls.eq
        elif func in [np.not_equal, '<>', 'ne', '-ne', '!=', 'not', 'not_equal', 'not equal to']:
            return cls.ne
        elif func in [np.greater, '>', 'gt', '-gt', 'above', 'after', 'greater', 'greater than']:
            return cls.gt
        elif func in [np.less, '<', 'lt', '-lt', 'below', 'before', 'less', 'less than']:
            return cls.lt
        elif func in [np.greater_equal, '>=', 'ge', '-ge', 'greater_equal', 'greater than or equal to']:
            return cls.ge
        elif func in [np.less_equal, '<=', 'le', '-le', 'less_equal', 'less than or equal to']:
            return cls.le
        raise ValueError('Invalid Comparison name: %s'%func)

#
# Control Condition classes
#

class ControlPriority(enum.Enum):
    very_low = 0
    low = 1
    medium_low = 2
    medium = 3
    medium_high = 4
    high = 5
    very_high = 6


class ControlCondition(six.with_metaclass(abc.ABCMeta, object)):
    """A base class for control conditions"""
    def __init__(self):
        self._backtrack = 0

    @abc.abstractmethod
    def requires(self):
        """Returns a list of objects required to evaluate this condition"""
        return []

    @property
    def name(self):
        return str(self)

    @property
    def backtrack(self):
        """Should be updated by the ``evaluate`` method if appropriate."""
        return self._backtrack

    def __hash__(self):
        return hash(self.name)

    @abc.abstractmethod
    def evaluate(self):
        pass

    def __bool__(self):
        return self.evaluate()
    __nonzero__ = __bool__

    @classmethod
    def _parse_value(cls, value):
        try:
            v = float(value)
            return v
        except ValueError:
            value = value.upper()
            if value == 'CLOSED':
                return 0
            if value == 'OPEN':
                return 1
            if value == 'ACTIVE':
                return np.nan
            PM = 0
            words = value.split()
            if len(words) > 1:
                if words[1] == 'PM':
                    PM = 86400 / 2
            hms = words[0].split(':')
            v = 0
            if len(hms) > 2:
                v += int(hms[2])
            if len(hms) > 1:
                v += int(hms[1])*60
            if len(hms) > 0:
                v += int(hms[0])*3600
            if int(hms[0]) <= 12:
                v += PM
            return v

    def _repr_value(self, attr, value):
        if attr.lower() in ['status'] and int(value) == value:
            return LinkStatus(int(value)).name
        return value

    @classmethod
    def _sec_to_hours_min_sec(cls, value):
        sec = float(value)
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        return '{:02d}:{:02d}:{:02d}'.format(hours, mm, int(sec))

    @classmethod
    def _sec_to_days_hours_min_sec(cls, value):
        sec = float(value)
        days = int(sec/86400.)
        sec -= days*86400
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        if days > 0:
            return '{}-{:02d}:{:02d}:{:02d}'.format(days, hours, mm, int(sec))
        else:
            return '{:02d}:{:02d}:{:02d}'.format(hours, mm, int(sec))

    @classmethod
    def _sec_to_clock(cls, value):
        sec = float(value)
        hours = int(sec/3600.)
        sec -= hours*3600
        mm = int(sec/60.)
        sec -= mm*60
        if hours >= 12:
            pm = 'PM'
            if hours > 12:
                hours -= 12
        elif hours == 0:
            pm = 'AM'
            hours = 12
        else:
            pm = 'AM'
        return '{}:{:02d}:{:02d} {}'.format(hours, mm, int(sec), pm)


class TimeOfDayCondition(ControlCondition):
    """Time-of-day or "clocktime" based condition statement.
    Resets automatically at 12 AM in clock time (shifted time) every day simulated. Evaluated
    from 12 AM the first day of the simulation, even if this is prior to simulation start.
    Unlike the ``SimTimeCondition``, greater-than and less-than relationships make sense, and
    reset at midnight.
    
    Parameters
    ----------
    model : WaterNetworkModel
        The model that the time is being compared against
    relation : str or None
        String options are 'at', 'after' or 'before'. The 'at' and None are equivalent, and only
        evaluate as True during the simulation step the time occurs. `after` evaluates as True
        from the time specified until midnight, `before` evaluates as True from midnight until
        the specified time.
    threshold : float or str
        The time (a ``float`` in decimal hours since 12 AM) used in the condition; if provided as a
        string in 'hh:mm[:ss] [am|pm]' format, the time will be parsed from the string
    repeat : bool, optional
        True by default; if False, allows for a single, timed trigger, and probably needs an
        entry for `first_day`; in this case a relation of `after` becomes True from the time until
        the end of the simulation, and `before` is True from the beginning of the simulation until
        the time specified.
    first_day : float, default=0
        Start rule on day `first_day`, with the first day of simulation as day 0
    """
    def __init__(self, model, relation, threshold, repeat=True, first_day=0):
        self._model = model
        if isinstance(threshold, str) and not ':' in threshold:
            self._threshold = float(threshold) * 3600.
        else:
            self._threshold = self._parse_value(threshold)
        if relation is None:
            self._relation = Comparison.eq
        else:
            self._relation = Comparison.parse(relation)
        self._first_day = first_day
        self._repeat = repeat
        self._backtrack = 0
        if model is not None and not self._repeat and self._threshold < model._start_clocktime and first_day < 1:
            self._first_day = 1

    @property
    def name(self):
        if not self._repeat:
            rep = '/Once'
        else:
            rep = '/Daily'
        if self._first_day > 0:
            start = '/FirstDay/{}'.format(self._first_day)
        else:
            start = '/'
        return 'ClockTime/{}/{}{}{}'.format(self._relation.text,
                                             self._sec_to_hours_min_sec(self._threshold),
                                             rep, start)

    def __repr__(self):
        fmt = '<TimeOfDayCondition: model, {}, {}, {}, {}>'
        return fmt.format(repr(self._relation.text), repr(self._sec_to_clock(self._threshold)),
                          repr(self._repeat), repr(self._first_day))

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        fmt = 'clock_time {:s} "{}"'.format(self._relation.symbol,
                                          self._sec_to_clock(self._threshold))
        if not self._repeat:
            fmt = '( ' + ' && clock_day == {} )'.format(self._first_day)
        elif self._first_day > 0:
            fmt = '( ' + ' && clock_day >= {} )'.format(self._first_day)
        return fmt

    def evaluate(self):
        cur_time = self._model._shifted_time
        prev_time = self._model._prev_shifted_time
        day = np.floor(cur_time/86400)
        if day < self._first_day:
            self._backtrack = None
            return False
        if self._repeat:
            cur_time = int(cur_time - self._threshold) % 86400
            prev_time = int(prev_time - self._threshold) % 86400
        else:
            cur_time = cur_time - self._first_day * 86400.
            prev_time = prev_time - self._first_day * 86400.
        if self._relation is Comparison.eq and (prev_time < self._threshold and self._threshold <= cur_time):
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.gt and cur_time >= self._threshold and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.gt and cur_time >= self._threshold and prev_time >= self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.lt and cur_time >= self._threshold and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return False
        elif self._relation is Comparison.lt and cur_time >= self._threshold and prev_time >= self._threshold:
            self._backtrack = 0
            return False
        else:
            self._backtrack = 0
            return False


class SimTimeCondition(ControlCondition):
    """Condition based on time since start of the simulation.
    Generally, the relation should be ``None`` (converted to "at") --
    then it is *only* evaluated "at" specific times. Using greater-than or less-than type
    relationships should be reserved for complex, multi-condition statements and
    should not be used for simple controls. If ``repeat`` is used, the relationship will
    automatically be changed to an "at time" evaluation, and a warning will be raised.
    
    Parameters
    ----------
    model : WaterNetworkModel
        The model that the time threshold is being compared against
    relation : str or None
        String options are 'at', 'after' or 'before'. The 'at' and None are equivalent, and only
        evaluate as True during the simulation step the time occurs. After evaluates as True
        from the time specified until the end of simulation, before evaluates as True from
        start of simulation until the specified time.
    threshold : float or str
        The time (a ``float`` in decimal hours) used in the condition; if provided as a string in
        '[dd-]hh:mm[:ss]' format, then the time will be parsed from the string;
    repeat : bool or float, default=False
        If True, then repeat every 24-hours; if non-zero float, reset the
        condition every `repeat` seconds after the first_time.
    first_time : float, default=0
        Start rule at `first_time`, using that time as 0 for the condition evaluation
    """
    def __init__(self, model, relation, threshold, repeat=False, first_time=0):
        self._model = model
        if isinstance(threshold, str) and not ':' in threshold:
            self._threshold = float(threshold) * 3600.
        else:
            self._threshold = self._parse_value(threshold)
        if relation is None:
            self._relation = Comparison.eq
        else:
            self._relation = Comparison.parse(relation)
        self._repeat = repeat
        if repeat is True:
            self._repeat = 86400
        self._backtrack = 0
        self._first_time = first_time

    @property
    def name(self):
        if not self._repeat:
            rep = ''
        else:
            rep = '%Every{}sec'.format(self._repeat)
        if self._first_time > 0:
            start = '#Start@{}sec'.format((self._first_time))
        else:
            start = ''
        return 'SimTime{}{}{}{}'.format(self._relation.symbol,
                                      (self._threshold),
                                      rep, start)

    def __repr__(self):
        fmt = '<SimTimeCondition: model, {}, {}, {}, {}>'
        return fmt.format(repr(self._relation.text), repr(self._sec_to_days_hours_min_sec(self._threshold)),
                          repr(self._repeat), repr(self._first_time))

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        fmt = '{} {} sec'.format(self._relation.symbol, self._threshold)
        if self._repeat is True:
            fmt = '% 86400.0 ' + fmt
        elif self._repeat > 0:
            fmt = '% {:.1f} '.format(int(self._repeat)) + fmt
        if self._first_time > 0:
            fmt = '(sim_time - {:d}) '.format(int(self._first_time)) + fmt
        else:
            fmt = 'sim_time ' + fmt
        return fmt

    def evaluate(self):
        cur_time = self._model.sim_time
        prev_time = self._model._prev_sim_time
        if self._repeat and cur_time > self._threshold:
            cur_time = (cur_time - self._threshold) % self._repeat
            prev_time = (prev_time - self._threshold) % self._repeat
        if self._relation is Comparison.eq and (prev_time < self._threshold and self._threshold <= cur_time):
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.gt and cur_time >= self._threshold and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.gt and cur_time >= self._threshold and prev_time >= self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.lt and cur_time >= self._threshold and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return False
        elif self._relation is Comparison.lt and cur_time >= self._threshold and prev_time >= self._threshold:
            self._backtrack = 0
            return False
        else:
            self._backtrack = 0
            return False


class ValueCondition(ControlCondition):
    """Compare a network element attribute to a set value
    This type of condition can be converted to an EPANET control or rule conditional clause.
    
    Parameters
    ----------
    source_obj : object
        The object (such as a Junction, Tank, Pipe, etc.) to use in the comparison
    source_attr : str
        The attribute of the object (such as level, pressure, setting, etc.) to
        compare against the threshold
    operation : function or str
        A two-parameter comparison function (e.g., numpy.greater, numpy.less_equal), or a
        string describing the comparison (e.g., '=', 'below', 'is', '>=', etc.)
        Words, such as 'below', are only accepted from the EPANET rules conditions list (see ...)
    threshold : float
        A value to compare the source object attribute against
    """
    def __new__(cls, source_obj, source_attr, relation, threshold):
        if isinstance(source_obj, wntr.network.Tank) and source_attr in {'level',  'pressure', 'head'}:
            return object.__new__(TankLevelCondition)
        else:
            return object.__new__(ValueCondition)

    def __init__(self, source_obj, source_attr, relation, threshold):
        self._source_obj = source_obj
        self._source_attr = source_attr
        self._relation = Comparison.parse(relation)
        self._threshold = ControlCondition._parse_value(threshold)
        self._backtrack = 0

    def requires(self):
        return [self._source_obj]

    @property
    def name(self):
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        else:
            obj = str(self._source_obj)

        return '{}:{}{}{}'.format(obj, self._source_attr,
                                self._relation.symbol, self._threshold)

    def __repr__(self):
        return "<ValueCondition: {}, {}, {}, {}>".format(str(self._source_obj),
                                                       str(self._source_attr),
                                                       str(self._relation.symbol),
                                                       str(self._threshold))

    def __str__(self):
        typ = self._source_obj.__class__.__name__
        obj = str(self._source_obj)
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        att = self._source_attr
        rel = self._relation.symbol
        val = self._repr_value(att, self._threshold)
        return "{}('{}').{} {} {}".format(typ, obj, att, rel, val)

    def evaluate(self):
        cur_value = getattr(self._source_obj, self._source_attr)
        thresh_value = self._threshold
        relation = self._relation.func
        if np.isnan(self._threshold):
            relation = np.greater
            thresh_value = 0.0
        state = relation(cur_value, thresh_value)
        return state


class TankLevelCondition(ValueCondition):
    def __init__(self, source_obj, source_attr, relation, threshold):
        super(TankLevelCondition, self).__init__(source_obj, source_attr, relation, threshold)
        assert source_attr in {'level', 'pressure', 'head'}
        self._last_value = getattr(self._source_obj, self._source_attr)  # this is used to see if backtracking is needed

    def evaluate(self):
        self._backtrack = 0  # no backtracking is needed unless specified in the if statement below
        cur_value = getattr(self._source_obj, self._source_attr)  # get the current tank level
        thresh_value = self._threshold
        relation = self._relation
        if np.isnan(self._threshold):  # what is this doing?
            relation = np.greater
            thresh_value = 0.0
        state = relation(cur_value, thresh_value)  # determine if the condition is satisfied
        if state and not relation(self._last_value, thresh_value):
            # if the condition is satisfied and the last value did not satisfy the condition, then backtracking
            # is needed
            self._backtrack = -(cur_value - thresh_value)*math.pi/4.0*self._source_obj.diameter**2/self._source_obj.demand
        self._last_value = cur_value  # update the last value
        return state


class RelativeCondition(ControlCondition):
    """Compare attributes of two different objects (e.g., levels from tanks 1 and 2)
    This type of condition does not work with the EpanetSimulator, only the WNTRSimulator.
    
    Parameters
    ----------
    source_obj : object
        The object (such as a Junction, Tank, Pipe, etc.) to use in the comparison
    source_attr : str
        The attribute of the object (such as level, pressure, setting, etc.) to
        compare against the threshold
    relation : function
        A numpy or other comparison method that takes two values and returns a bool
        (e.g., numpy.greater, numpy.less_equal)
    threshold_obj : object
        The object (such as a Junction, Tank, Pipe, etc.) to use in the comparison of attributes
    threshold_attr : str
        The attribute to used in the comparison evaluation
    """
    def __init__(self, source_obj, source_attr, relation, threshold_obj, threshold_attr):
        self._source_obj = source_obj
        self._source_attr = source_attr
        self._relation = Comparison.parse(relation)
        self._threshold_obj = threshold_obj
        self._threshold_attr = threshold_attr
        self._backtrack = 0

    @property
    def name(self):
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        else:
            obj = str(self._source_obj)
        if hasattr(self._threshold_obj, 'name'):
            tobj = self._threshold_obj.name
        else:
            tobj = str(self._threshold_obj)
        return '{}:{}_{}_{}:{}'.format(obj, self._source_attr,
                                self._relation.symbol,
                                tobj, self._threshold_attr)

    def requires(self):
        return [self._source_obj, self._threshold_obj]

    def __repr__(self):
        return "RelativeCondition({}, {}, {}, {}, {})".format(str(self._source_obj),
                                                              str(self._source_attr),
                                                              str(self._relation),
                                                              str(self._threshold_obj),
                                                              str(self._threshold_attr))

    def __str__(self):
        typ = self._source_obj.__class__.__name__
        obj = str(self._source_obj)
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        att = self._source_attr
        rel = self._relation.symbol
        ttyp = self._threshold_obj.__class__.__name__
        if hasattr(self._threshold_obj, 'name'):
            tobj = self._threshold_obj.name
        else:
            tobj = str(self._threshold_obj)
        tatt = self._threshold_attr
        fmt = "{}('{}').{} {} {}('{}').{}"
        return fmt.format(typ, obj, att,
                          rel,
                          ttyp, tobj, tatt)

    def evaluate(self):
        cur_value = getattr(self._source_obj, self._source_attr)
        thresh_value = getattr(self._threshold_obj, self._threshold_attr)
        relation = self._relation.func
        state = relation(cur_value, thresh_value)
        return state


class OrCondition(ControlCondition):
    """Combine two WNTR Conditions with an OR.
    
    Parameters
    ----------
    cond1 : ControlCondition
        The first condition
    cond2 : ControlCondition
        The second condition
    Returns
    -------
    bool
        True if either condition evaluates to True; otherwise False
    """
    def __init__(self, cond1, cond2):
        self._condition_1 = cond1
        self._condition_2 = cond2

    def __str__(self):
        return "( " + str(self._condition_1) + " || " + str(self._condition_2) + " )"

    def __repr__(self):
        return 'Or({}, {})'.format(repr(self._condition_1), repr(self._condition_2))

    def evaluate(self):
        return bool(self._condition_1) or bool(self._condition_2)

    @property
    def backtrack(self):
        return np.max([self._condition_1.backtrack, self._condition_2.backtrack])

    def requires(self):
        return self._condition_1.requires() + self._condition_2.requires()


class AndCondition(ControlCondition):
    """Combine two WNTR Conditions with an AND
    
    Parameters
    ----------
    cond1 : ControlCondition
        The first condition
    cond2 : ControlCondition
        The second condition
    Returns
    -------
    bool
        True if both conditions evaluate to True; otherwise False
    """
    def __init__(self, cond1, cond2):
        self._condition_1 = cond1
        self._condition_2 = cond2

    def __str__(self):
        return "( "+ str(self._condition_1) + " && " + str(self._condition_2) + " )"

    def __repr__(self):
        return 'And({}, {})'.format(repr(self._condition_1), repr(self._condition_2))

    def evaluate(self):
        return bool(self._condition_1) and bool(self._condition_2)

    @property
    def backtrack(self):
        return np.min([self._condition_1.backtrack, self._condition_2.backtrack])

    def requires(self):
        return self._condition_1.requires() + self._condition_2.requires()


class _CloseCVCondition(ControlCondition):
    Htol = 0.0001524
    Qtol = 2.83168e-6

    def __init__(self, wn, cv):
        self._cv = cv
        self._start_node = wn.get_node(cv.start_node)
        self._end_node = wn.get_node(cv.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._cv, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the cv needs to be closed
        """
        dh = self._start_node.head - self._end_node.head
        if abs(dh) > self.Htol:
            if dh < -self.Htol:
                return True
            elif self._cv.flow < -self.Qtol:
                return True
            else:
                return False
        else:
            if self._cv.flow < -self.Qtol:
                return True
            else:
                return False


class _OpenCVCondition(ControlCondition):
    Htol = 0.0001524
    Qtol = 2.83168e-6

    def __init__(self, wn, cv):
        self._cv = cv
        self._start_node = wn.get_node(cv.start_node)
        self._end_node = wn.get_node(cv.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._cv, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the cv needs to be closed
        """
        dh = self._start_node.head - self._end_node.head
        if abs(dh) > self.Htol:
            if dh < -self.Htol:
                return False
            elif self._cv.flow < -self.Qtol:
                return False
            else:
                return True
        else:
            return False


class _ClosePowerPumpCondition(ControlCondition):
    """
    Prevents reverse flow in pumps.
    """
    Htol = 0.0001524
    Qtol = 2.83168e-6
    Hmax = 1e10

    def __init__(self, wn, pump):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        pump: wntr.network.Pump
        """
        self._pump = pump
        self._start_node = wn.get_node(pump.start_node)
        self._end_node = wn.get_node(pump.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._pump, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        dh = self._end_node.head - self._start_node.head
        if dh > self.Hmax + self.Htol:
            return True
        return False


class _OpenPowerPumpCondition(ControlCondition):
    Htol = 0.0001524
    Qtol = 2.83168e-6
    Hmax = 1e10

    def __init__(self, wn, pump):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        pump: wntr.network.Pump
        """
        self._pump = pump
        self._start_node = wn.get_node(pump.start_node)
        self._end_node = wn.get_node(pump.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._pump, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the pump needs to be opened
        """
        dh = self._end_node.head - self._start_node.head
        if dh <= self.Hmax + self.Htol:
            return True
        return False


class _CloseHeadPumpCondition(ControlCondition):
    """
    Prevents reverse flow in pumps.
    """
    Htol = 0.0001524

    def __init__(self, wn, pump):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        pump: wntr.network.Pump
        """
        self._pump = pump
        self._start_node = wn.get_node(pump.start_node)
        self._end_node = wn.get_node(pump.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._pump, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        dh = self._end_node.head - self._start_node.head
        if dh > self.Hmax + self.Htol:
            return True


class _OpenHeadPumpCondition(ControlCondition):
    """
    Prevents reverse flow in pumps.
    """
    Htol = 0.0001524

    def __init__(self, wn, pump):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        pump: wntr.network.Pump
        """
        self._pump = pump
        self._start_node = wn.get_node(pump.start_node)
        self._end_node = wn.get_node(pump.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._pump, self._start_node, self._end_node]

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        dh = self._end_node.head - self._start_node.head
        if dh <= self.Hmax + self.Htol:
            return True


class _ClosePRVCondition(ControlCondition):
    _Qtol = 2.83168e-6

    def __init__(self, prv):
        """
        Parameters
        ----------
        prv: wntr.network.Valve
        """
        self._prv = prv
        self._backtrack = 0

    def requires(self):
        return [self._prv]

    def evaluate(self):
        if self._prv._internal_status == wntr.network.LinkStatus.Active:
            if self._prv.flow < -self._Qtol:
                return True
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Open:
            if self._prv.flow < -self._Qtol:
                return True
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Closed:
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))


class _OpenPRVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, prv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        prv: wntr.network.Valve
        """
        self._prv = prv
        self._start_node = wn.get_node(self._prv.start_node)
        self._end_node = wn.get_node(self._prv.end_node)
        self._backtrack = 0
        self._r = 0.0826 * 0.02 * self._prv.diameter ** (-4) * 2.0

    def requires(self):
        return [self._prv, self._start_node, self._end_node]

    def evaluate(self):
        if self._prv._internal_status == wntr.network.LinkStatus.Active:
            if self._prv.flow < -self._Qtol:
                return False
            elif self._start_node.head < self._prv.setting + self._end_node.elevation  + self._r * abs(self._prv.flow)**2 - self._Htol:
                return True
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Open:
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Closed:
            if ((self._start_node.head > self._end_node.head + self._Htol) and
                    (self._start_node.head < self._prv.setting + self._end_node.elevation - self._Htol)):
                return True
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))


class _ActivePRVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, prv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        prv: wntr.network.Valve
        """
        self._prv = prv
        self._start_node = wn.get_node(self._prv.start_node)
        self._end_node = wn.get_node(self._prv.end_node)
        self._backtrack = 0
        self._r = 0.0826 * 0.02 * self._prv.diameter ** (-4) * 2.0

    def requires(self):
        return [self._prv, self._start_node, self._end_node]

    def evaluate(self):
        if self._prv._internal_status == wntr.network.LinkStatus.Active:
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Open:
            if self._prv.flow < -self._Qtol:
                return False
            elif (self._start_node.head > self._prv.setting + self._end_node.elevation +
                  self._r * abs(self._prv.flow)**2 + self._Htol):
                return True
            return False
        elif self._prv._internal_status == wntr.network.LinkStatus.Closed:
            if ((self._start_node.head > self._end_node.head + self._Htol) and
                    (self._start_node.head < self._prv.setting + self._end_node.elevation - self._Htol)):
                return False
            elif ((self._start_node.head > self._end_node.head + self._Htol) and
                  (self._end_node.head < self._prv.setting + self._end_node.elevation - self._Htol)):
                return True
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))


class _OpenFCVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, fcv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        fcv: wntr.network.Valve
        """
        self._fcv = fcv
        self._start_node = wn.get_node(self._fcv.start_node)
        self._end_node = wn.get_node(self._fcv.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._fcv, self._start_node, self._end_node]

    def evaluate(self):
        if self._start_node.head - self._end_node.head < -self._Htol:
            return True
        elif self._fcv.flow < -self._Qtol:
            return True
        else:
            return False


class _ActiveFCVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, fcv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        fcv: wntr.network.Valve
        """
        self._fcv = fcv
        self._start_node = wn.get_node(self._fcv.start_node)
        self._end_node = wn.get_node(self._fcv.end_node)
        self._backtrack = 0

    def requires(self):
        return [self._fcv, self._start_node, self._end_node]

    def evaluate(self):
        if self._start_node.head - self._end_node.head < -self._Htol:
            return False
        elif self._fcv.flow < -self._Qtol:
            return False
        elif self._fcv._internal_status == wntr.network.LinkStatus.Open and self._fcv.flow >= self._fcv.setting:
            return True
        else:
            return False


class _ValveNewSettingCondition(ControlCondition):
    def __init__(self, valve):
        """
        Parameters
        ----------
        valve: wntr.network.Valve
        """
        self._valve = valve

    def requires(self):
        return [self._valve]

    def evaluate(self):
        if self._valve.setting != self._valve._prev_setting:
            return True
        return False


class BaseControlAction(six.with_metaclass(abc.ABCMeta, Subject)):
    """
    A base class for deriving new control actions. The control action is run by calling RunControlAction
    This class is not meant to be used directly. Derived classes must implement the RunControlAction method.
    """
    @abc.abstractmethod
    def run_control_action(self):
        """
        This method is called to run the corresponding control action.
        """
        pass

    @abc.abstractmethod
    def requires(self):
        """Returns a list of objects used to evaluate the control"""
        pass

    @abc.abstractmethod
    def target(self):
        """
        Returns a tuple (object, attribute) containing the object and attribute that the control action may change

        Returns
        target: tuple
        """
        pass


class ControlAction(BaseControlAction):
    """
    A general class for specifying a control action that simply modifies the attribute of an object (target).
    
    Parameters
    ----------
    target_obj : object
        The object whose attribute will be changed when the control runs.
    attribute : string
        The attribute that will be changed on the target_obj when the control runs.
    value : any
        The new value for target_obj.attribute when the control runs.
    """
    def __init__(self, target_obj, attribute, value):
        if target_obj is None:
            raise ValueError('target_obj is None in ControlAction::__init__. A valid target_obj is needed.')
        if not hasattr(target_obj, attribute):
            raise ValueError('attribute given in ControlAction::__init__ is not valid for target_obj')

        self._target_obj = target_obj
        self._attribute = attribute
        self._value = value

    def requires(self):
        return [self._target_obj]

    def __repr__(self):
        return '<ControlAction: {}, {}, {}>'.format(str(self._target_obj), str(self._attribute), str(self._repr_value()))

    def __str__(self):
        return "set {}('{}').{} to {}".format(self._target_obj.__class__.__name__,
                                       self._target_obj.name,
                                       self._attribute,
                                       self._repr_value())

    def _repr_value(self):
        if self._attribute.lower() in ['status']:
            return wntr.network.model.LinkStatus(int(self._value)).name
        return self._value

    def __eq__(self, other):
        if self._target_obj == other._target_obj and \
           self._attribute      == other._attribute:
            if type(self._value) == float:
                if abs(self._value - other._value)<1e-10:
                    return True
                return False
            else:
                if self._value == other._value:
                    return True
                return False
        else:
            return False

    def __hash__(self):
        return id(self)

    def run_control_action(self):
        """
        Activate the control action.
        """
        setattr(self._target_obj, self._attribute, self._value)
        self.notify()

    def target(self):
        return self._target_obj, self._attribute


class _InternalControlAction(BaseControlAction):
    """
    A control action class that modifies a private attribute in order to change a property on an object. For example,
    a valve has a status property, but the control action must act on the _internal_status.

    Parameters
    ----------
    target_obj: object
        The object for which an attribute is being changed.
    internal_attribute: str
        The attribute being modified (e.g., _internal_stats)
    value: any
        The new value for the internal_attribute
    property_attribute: str
        The attribute to be checked for an actual change (e.g., status)
    """
    def __init__(self, target_obj, internal_attribute, value, property_attribute):
        if not hasattr(target_obj, internal_attribute):
            raise AttributeError('{0} does not have attribute {1}'.format(target_obj, internal_attribute))
        if not hasattr(target_obj, property_attribute):
            raise AttributeError('{0} does not have attribute {1}'.format(target_obj, property_attribute))

        self._target_obj = target_obj
        self._internal_attr = internal_attribute
        self._value = value
        self._property_attr = property_attribute

    def requires(self):
        """
        Return a list of objects required by the control action.

        Returns
        -------
        required_objects: list of object
        """
        return [self._target_obj]

    def run_control_action(self):
        """
        Activate the control action.
        """
        if self._target_obj is None:
            raise ValueError('target is None inside _InternalControlAction::RunControlAction.' +
                             'This may be because a target_obj was added, but later the object itself was deleted.')
        setattr(self._target_obj, self._internal_attr, self._value)
        self.notify()

    def target(self):
        """
        Returns a tuple containing the target object and the attribute to check for modification.

        Returns
        -------
        target: tuple
        """
        return self._target_obj, self._property_attr

    def __repr__(self):
        return '<_InternalControlAction: {}, {}, {}>'.format(str(self._target_obj), self._internal_attr,
                                                             str(self._value))

    def __str__(self):
        return "set {}('{}').{} to {}".format(self._target_obj.__class__.__name__,
                                              self._target_obj.name,
                                              self._internal_attr,
                                              self._value)

    def __eq__(self, other):
        if ((self._target_obj == other._target_obj) and
            (self._internal_attr == other._internal_attr) and
            (self._property_attr == other._property_attr)):
            if type(self._value) == float:
                if abs(self._value - other._value)<1e-10:
                    return True
                return False
            else:
                if self._value == other._value:
                    return True
                return False
        else:
            return False

    def __hash__(self):
        return id(self)


#
# Control classes
#

class ControlBase(six.with_metaclass(abc.ABCMeta, object)):
    """
    This is the base class for all control objects. Control objects are used to check the conditions under which a
    ControlAction should be run. For example, if a pump is supposed to be turned on when the simulation time
    reaches 6 AM, the ControlAction would be "turn the pump on", and the Control would be "when the simulation
    reaches 6 AM".
    From an implementation standpoint, derived Control classes implement a particular mechanism for monitoring state
    (e.g. checking the simulation time to see if a change should be made). Then, they typically call RunControlAction
    on a derived ControlAction class.
    New Control classes (classes derived from Control) must implement the following methods:
    - _IsControlActionRequiredImpl(self, wnm, presolve_flag)
    - _RunControlActionImpl(self, wnm, priority)
    """
    @abc.abstractmethod
    def is_control_action_required(self, wnm, presolve_flag):
        """
        This method is called to see if any action is required by this control object. This method returns a tuple
        that indicates if action is required (a bool) and a recommended time for the simulation to backup (in seconds
        as a positive int).
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated.
        presolve_flag : bool
            This is true if we are calling before the solve, and false if we are calling after the solve (within the
            current timestep).
        """
        pass

    @abc.abstractmethod
    def run_control_action(self, wnm, priority):
        """
        This method is called to run the control action after a call to IsControlActionRequired indicates that an
        action is required.
        Note: Derived classes should not override this method, but should override _RunControlActionImpl instead.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        pass

    @abc.abstractmethod
    def requires(self):
        """Returns a list of objects required to evaluate this control"""
        return []

    @abc.abstractmethod
    def actions(self):
        pass


class Control(ControlBase):
    """If-Then[-Else] contol
    """
    def __init__(self, condition, then_actions, else_actions=None, priority=ControlPriority.very_low, name=None):
        if not isinstance(condition, ControlCondition):
            raise ValueError('The conditions argument must be a ControlCondition instance')
        self._condition = condition
        if isinstance(then_actions, Iterable):
            self._then_actions = list(then_actions)
        elif then_actions is not None:
            self._then_actions = [then_actions]
        else:
            self._then_actions = []
        if isinstance(else_actions, Iterable):
            self._else_actions = list(else_actions)
        elif else_actions is not None:
            self._else_actions = [else_actions]
        else:
            self._else_actions = []
        self._which = None
        self._priority = priority
        self._name = name
        if self._name is None:
            self._name = ''

    def requires(self):
        req = self._condition.requires()
        for action in self._then_actions:
            req += action.requires()
        for action in self._else_actions:
            req += action.requires()
        return req

    def actions(self):
        return self._then_actions + self._else_actions

    @property
    def name(self):
        if self._name is not None:
            return self._name
        else:
            return '/'.join(str(self).split())

    def __repr__(self):
        fmt = "<IfThenElseControl: '{}', {}, {}, {}, priority={}>"
        return fmt.format(self._name, repr(self._condition), repr(self._then_actions), repr(self._else_actions), self._priority)

    def __str__(self):
        text = 'Rule {} := if {}'.format(self._name, self._condition)
        if self._then_actions is not None and len(self._then_actions) > 0:
            then_text = ' then '
            for ct, act in enumerate(self._then_actions):
                if ct == 0:
                    then_text += str(act)
                else:
                    then_text += ' and {}'.format(str(act))
            text += then_text
        if self._else_actions is not None and len(self._else_actions) > 0:
            else_text = ' else '
            for ct, act in enumerate(self._else_actions):
                if ct == 0:
                    else_text += str(act)
                else:
                    else_text += ' and {}'.format(str(act))
            text += else_text
        if self._priority is not None and self._priority >= 0:
            text += ' with priority {}'.format(self._priority)
        return text

    def is_control_action_required(self, wnm, presolve_flag):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated.
        presolve_flag : bool
            This is true if we are calling before the solve, and false if we are calling after the solve (within the
            current timestep).
        """
        do = self._condition.evaluate()
        back = self._condition.backtrack
        if not presolve_flag:
            back = 0
        if do:
            self._which = 'then'
            return True, back
        elif not do and self._else_actions is not None and len(self._else_actions) > 0:
            self._which = 'else'
            return (True, back)
        else:
            return (False, None)

    def run_control_action(self, wnm, priority):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        if self._priority != priority:
            return None
        if self._which == 'then':
            for control_action in self._then_actions:
                control_action.run_control_action()
        elif self._which == 'else':
            for control_action in self._else_actions:
                control_action.run_control_action()
        else:
            raise RuntimeError('control actions called even though if-then statement was False')

    @classmethod
    def time_control(cls, wnm, run_at_time, time_flag, daily_flag, control_action):
        """
        Parameters
        ----------
        wnm: wntr.network.WaterNetworkModel
        run_at_time: int
        time_flag: str
        daily_flag: bool
        control_action: BaseControlAction
        """
        if time_flag.upper() == 'SIM_TIME':
            condition = SimTimeCondition(model=wnm, relation=Comparison.eq, threshold=run_at_time, repeat=daily_flag,
                                         first_time=0)
        elif time_flag.upper() == 'CLOCK_TIME':
            condition = TimeOfDayCondition(model=wnm, relation=Comparison.eq, threshold=run_at_time, repeat=daily_flag,
                                           first_day=0)
        else:
            raise ValueError("time_flag not recognized; expected either 'sim_time' or 'clock_time'")

        return Control(condition=condition, then_actions=[control_action], else_actions=[])

    @classmethod
    def conditional_control(cls, source_obj, source_attr, operation, threshold, control_action):
        condition = ValueCondition(source_obj=source_obj, source_attr=source_attr, relation=operation,
                                   threshold=threshold)
        return Control(condition=condition, then_actions=[control_action], else_actions=[])


class ControlManager(Observer):
    def __init__(self):
        self._controls = OrderedSet()
        self._previous_values = OrderedDict()  # {(obj, attr): value}
        self._changed = OrderedSet()  # set of (obj, attr) that has been changed from _previous_values

    def update(self, subject):
        """
        The update method gets called when a subject (control action) is activated.

        Paramters
        ---------
        subject: BaseControlAction
        """
        for obj, attr in subject.targets():
            if getattr(obj, attr) == self._previous_values[(obj, attr)]:
                self._changed.discard((obj, attr))
            else:
                self._changed.add((obj, attr))

    def register_control(self, control):
        """
        Register a control with the ControlManager

        Parameters
        ----------
        control: Control
        """
        self._controls.add(control)
        for action in control.actions():
            action.subscribe(self)
            for obj, attr in action.targets():
                self._previous_values[(obj, attr)] = getattr(obj, attr)

    def reset(self):
        self._previous_values = OrderedDict()
        for control in self._controls:
            for action in control.actions():
                for obj, attr in action.targets():
                    self._previous_values[(obj, attr)] = getattr(obj, attr)

    def update_previous_values(self):
        for obj, attr in self._changed:
            self._previous_values[(obj, attr)] = getattr(obj, attr)
        self._changed.clear()

    def changes_made(self):
        if len(self._changed) > 0:
            return True
        return False

    def get_changes(self):
        for obj, attr in self._changed:
            yield obj, attr