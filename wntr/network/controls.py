"""
The wntr.network.controls module includes methods to define network controls
and control actions.  These controls modify parameters in the network during
simulation.

.. rubric:: Contents

.. autosummary::

    Subject
    Observer
    Comparison
    ControlPriority
    ControlCondition
    TimeOfDayCondition
    SimTimeCondition
    ValueCondition
    TankLevelCondition
    RelativeCondition
    OrCondition
    AndCondition
    BaseControlAction
    ControlAction
    ControlBase
    Control
    ControlManager
	
"""
import math
import enum
import numpy as np
import logging
import six
from .elements import LinkStatus
import abc
from wntr.utils.ordered_set import OrderedSet
from collections import OrderedDict
from .elements import Tank, Junction, Valve, Pump, Reservoir, Pipe
from wntr.utils.doc_inheritor import DocInheritor
import warnings
from typing import Hashable, Dict, Any, Tuple, MutableSet, Iterable

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

def _ensure_iterable(to_check: Any)->Iterable[Any]:
    """Make sure the input is interable

    Parameters
    ----------
    to_check : Any
        The input to check which can be of any type including None

    Returns
    -------
    Iterable[Any]
        to_check as an iterable object, if None an empty list is returned
    """
    if isinstance(to_check, Iterable):
        to_return = list(to_check)
    elif to_check is not None:
        to_return = [to_check]
    else:
        to_return = []
    return to_return

class Subject(object):
    """
    A subject base class for the observer design pattern
    """
    def __init__(self):
        self._observers = OrderedSet()

    def subscribe(self, observer):
        """
        Subscribe observer to this subject. The update method of any observers of this subject will be called when
        notify is called on this subject.

        Parameters
        ----------
        observer: Observer
        """
        self._observers.add(observer)

    def unsubscribe(self, observer):
        """
        Unsubscribe observer from this subject.

        Parameters
        ----------
        observer: Observer
        """
        self._observers.remove(observer)

    def notify(self):
        """
        Call the update method for all observers of this subject.
        """
        for o in self._observers:
            o.update(self)


class Observer(six.with_metaclass(abc.ABCMeta, object)):
    """
    A base class for observers in the observer design pattern.
    """
    @abc.abstractmethod
    def update(self, subject):
        """
        This method is called when the subject being observed calls notify.

        Parameters
        ----------
        subject: Subject
            The subject that called notify.
        """
        pass


class Comparison(enum.Enum):
    """
    An enum class for comparison operators.

    .. rubric:: Enum Members

    ===========  ==============================================
    :attr:`~gt`  greater than
    :attr:`~ge`  greater than or equal to
    :attr:`~lt`  less than
    :attr:`~le`  less than or equal to
    :attr:`~eq`  equal to
    :attr:`~ne`  not equal to
    ===========  ==============================================

    """
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
        value = getattr(self, '_value_')
        return value[1]
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
        elif isinstance(func, cls):
            func = func.func
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


class ControlPriority(enum.IntEnum):
    """
    An enum class for control priorities.

    .. rubric:: Enum Members

    ====================  =====================================================
    :attr:`~very_low`     very low priority
    :attr:`~low`          low priority
    :attr:`~medium_low`   medium low priority
    :attr:`~medium`       medium priority
    :attr:`~medium_high`  medium high priority
    :attr:`~high`         high priority
    :attr:`~very_high`    very high priority
    ====================  =====================================================

    """
    very_low = 0
    low = 1
    medium_low = 2
    medium = 3
    medium_high = 4
    high = 5
    very_high = 6


class _ControlType(enum.Enum):
    presolve = 0
    postsolve = 1
    rule = 2
    pre_and_postsolve = 3
    feasibility = 4  # controls necessary to ensure the problem being solved is feasible


class ControlCondition(six.with_metaclass(abc.ABCMeta, object)):
    """A base class for control conditions"""
    def __init__(self):
        self._backtrack = 0

    def _reset(self):
        pass

    @abc.abstractmethod
    def requires(self):
        """
        Returns a set of objects required to evaluate this condition

        Returns
        -------
        required_objects: OrderedSet of object
        """
        return OrderedSet()

    @property
    def name(self):
        """
        Returns the string representation of the condition.

        Returns
        -------
        name: str
        """
        return str(self)

    @property
    def backtrack(self):
        """
        The amount of time by which the simulation should be backed up.
        Should be updated by the :class:`~wntr.network.controls.ControlCondition.evaluate` method if appropriate.

        Returns
        -------
        backtrack: int
        """
        return self._backtrack

    @abc.abstractmethod
    def evaluate(self):
        """
        Check if the condition is satisfied.

        Returns
        -------
        check: bool
        """
        pass

    def __bool__(self):
        """
        Check if the condition is satisfied.

        Returns
        -------
        check: bool
        """
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
                return 2
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
        if attr.lower() in ['status'] and isinstance(value, str):
            return value.upper()
        if attr.lower() in ['status'] and int(value) == value:
            return LinkStatus(int(value)).name.upper()
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


@DocInheritor({'requires', 'evaluate', 'name'})
class TimeOfDayCondition(ControlCondition):
    """Time-of-day or "clocktime" based condition statement.
    Resets automatically at 12 AM in clock time (shifted time) every day simulated. Evaluated
    from 12 AM the first day of the simulation, even if this is prior to simulation start.
    Unlike the :class:`~wntr.network.controls.SimTimeCondition`, greater-than and less-than
    relationships make sense, and reset at midnight.
    
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

    TODO:  WE ARE NOT TESTING THIS!!!!
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
        if model is not None and not self._repeat and self._threshold < model.options.time.start_clocktime and first_day < 1:
            self._first_day = 1

    def _compare(self, other):
        """
        Parameters
        ----------
        other: TimeOfDayCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if abs(self._threshold - other._threshold) > 1e-10:
            return False
        if self._relation != other._relation:
            return False
        if self._first_day != other._first_day:
            return False
        if self._repeat != other._repeat:
            return False
        return True

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

    def requires(self):
        return OrderedSet()

    def __repr__(self):
        fmt = '<TimeOfDayCondition: model, {}, {}, {}, {}>'
        return fmt.format(repr(self._relation.text), repr(self._sec_to_clock(self._threshold)),
                          repr(self._repeat), repr(self._first_day))

    def __str__(self):
        fmt = 'SYSTEM CLOCKTIME {:s} {}'.format(self._relation.text.upper(),
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


@DocInheritor({'requires', 'evaluate', 'name'})
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

    def _compare(self, other):
        """
        Parameters
        ----------
        other: SimTimeCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if abs(self._threshold - other._threshold) > 1e-10:
            return False
        if self._repeat != other._repeat:
            return False
        if self._first_time != other._first_time:
            return False
        if self._relation != other._relation:
            return False
        return True

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

    def __str__(self):
        fmt = 'SYSTEM TIME {} {}'.format(self._relation.text.upper(), self._sec_to_hours_min_sec(self._threshold))
        if self._repeat is True:
            fmt = '% 86400.0 ' + fmt
        elif self._repeat > 0:
            fmt = '% {:.1f} '.format(int(self._repeat)) + fmt
        if self._first_time > 0:
            fmt = '(sim_time - {:d}) '.format(int(self._first_time)) + fmt
        else:
            fmt = '' + fmt
        return fmt

    def requires(self):
        return OrderedSet()

    def evaluate(self):
        cur_time = self._model.sim_time
        prev_time = self._model._prev_sim_time
        if self._repeat and cur_time > self._threshold:
            cur_time = (cur_time - self._threshold) % self._repeat
            prev_time = (prev_time - self._threshold) % self._repeat
        if self._relation is Comparison.eq and (prev_time < self._threshold and self._threshold <= cur_time):
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.gt and cur_time > self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.ge and cur_time >= self._threshold and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return True
        elif self._relation is Comparison.ge and cur_time >= self._threshold and prev_time >= self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.lt and cur_time < self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.le and cur_time <= self._threshold:
            self._backtrack = 0
            return True
        elif self._relation is Comparison.le and prev_time < self._threshold:
            self._backtrack = int(cur_time - self._threshold)
            return True
        else:
            self._backtrack = 0
            return False


@DocInheritor({'requires', 'evaluate', 'name'})
class ValueCondition(ControlCondition):
    """Compare a network element attribute to a set value.

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
        if isinstance(source_obj, Tank) and source_attr in {'level',  'pressure', 'head'}:
            return object.__new__(TankLevelCondition)
        else:
            return object.__new__(ValueCondition)
    
    def __getnewargs__(self):
        return self._source_obj, self._source_attr, self._relation, self._threshold
    
    def __init__(self, source_obj, source_attr, relation, threshold):
        self._source_obj = source_obj
        self._source_attr = source_attr
        self._relation = Comparison.parse(relation)
        self._threshold = ControlCondition._parse_value(threshold)
        self._backtrack = 0

    def _compare(self, other):
        """
        Parameters
        ----------
        other: ValueCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if not self._source_obj._compare(other._source_obj):
            return False
        if self._source_attr != other._source_attr:
            return False
        if abs(self._threshold - other._threshold) > 1e-10:
            return False
        if self._relation != other._relation:
            return False
        return True

    def requires(self):
        return OrderedSet([self._source_obj])

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
        if 'Pump' in typ:
            typ = 'Pump'
        elif 'Valve' in typ:
            typ = 'Valve'
        obj = str(self._source_obj)
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        att = self._source_attr
        rel = self._relation.text
        val = self._repr_value(att, self._threshold)
        return "{} {} {} {} {}".format(typ.upper(), obj, att.upper(), rel.upper(), val)

    def evaluate(self):
        cur_value = getattr(self._source_obj, self._source_attr)
        thresh_value = self._threshold
        relation = self._relation.func
        if np.isnan(self._threshold):
            relation = np.greater
            thresh_value = 0.0
        state = relation(np.round(cur_value,10), np.round(thresh_value,10))
        return bool(state)


@DocInheritor({'requires', 'evaluate', 'name'})
class FunctionCondition(ControlCondition):
    """
    A ControlCondition which calls a function to determine
    if the control needs activated or not. If the function
    returns True, then the control is activated.
    """
    def __init__(self, func, func_kwargs=None, requires=None):
        super(FunctionCondition, self).__init__()
        self._func = func
        if func_kwargs is None:
            self._func_kwargs = dict()
        else:
            self._func_kwargs = func_kwargs
        if requires is None:
            self._requires = OrderedSet()
        else:
            self._requires = OrderedSet(requires)

    def evaluate(self):
        return bool(self._func(**self._func_kwargs))

    def requires(self):
        return self._requires


@DocInheritor({'requires', 'evaluate'})
class TankLevelCondition(ValueCondition):
    """
    A special type of ValueCondition for tank levels/heads/pressures.
    """
    def __init__(self, source_obj, source_attr, relation, threshold):
        relation = Comparison.parse(relation)
        if relation not in {Comparison.ge, Comparison.le, Comparison.gt, Comparison.lt}:
            raise ValueError('TankLevelConditions only support <= and >= relations.')
        super(TankLevelCondition, self).__init__(source_obj, source_attr, relation, threshold)
        assert source_attr in {'level', 'pressure', 'head'}
        # this is used to see if backtracking is needed
        self._last_value = getattr(self._source_obj, self._source_attr)  


    def _reset(self):
        self._last_value = getattr(self._source_obj, self._source_attr)  # this is used to see if backtracking is needed

    def _compare(self, other):
        """
        Parameters
        ----------
        other: TankLevelCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if not self._source_obj._compare(other._source_obj):
            return False
        if self._source_attr != other._source_attr:
            return False
        if abs(self._threshold - other._threshold) > 1e-10:
            return False
        if self._relation != other._relation:
            return False
        return True

    def evaluate(self):
        self._backtrack = 0  # no backtracking is needed unless specified in the if statement below
        cur_value = getattr(self._source_obj, self._source_attr)  # get the current tank level, head, or pressure
        thresh_value = self._threshold
        relation = self._relation
        if relation is Comparison.gt:
            relation = Comparison.ge
        if relation is Comparison.lt:
            relation = Comparison.le
        if np.isnan(self._threshold):  # what is this doing?
            relation = np.greater
            thresh_value = 0.0
        state = relation(np.round(cur_value,10), np.round(thresh_value,10))  # determine if the condition is satisfied
        if state and not relation(np.round(self._last_value,10), np.round(thresh_value,10)):
            # if the condition is satisfied and the last value did not satisfy the condition, then backtracking
            # is needed.
            # The math.floor is not actually needed, but I leave it here for clarity. We want the backtrack value to be
            # slightly lower than what the floating point computation would give. This ensures the next time step will
            # be slightly later than when the tank level hits the threshold. This ensures the tank level will go
            # slightly beyond the threshold. This ensures that relation(self._last_value, thresh_value) will be True
            # next time. This prevents us from computing very small backtrack values over and over.
            if self._source_obj.demand != 0 and not self._source_obj.demand is None:
                if self._source_obj.vol_curve is None:
                    self._backtrack = int(math.floor((cur_value - thresh_value)
                             *math.pi/4.0*self._source_obj.diameter**2
                             /self._source_obj.demand))
                else: # a volume curve must be used instead
                    if self._source_attr == 'head':
                        thresh_level = thresh_value - self._source_obj.elevation
                        level = cur_value - self._source_obj.elevation
                    elif self._source_attr == 'level':
                        thresh_level = thresh_value
                        level = cur_value
                    else:
                        raise NotImplementedError("Pressure tank value conditions with a " + 
                                                     "volume curve have not been implemented.")
                    
                    cur_value_volume = self._source_obj.get_volume(level)
                    thresh_volume = self._source_obj.get_volume(thresh_level)
                    
                    self._backtrack = int(math.floor((cur_value_volume 
                                                      - thresh_volume) 
                                                      / self._source_obj.demand))
        self._last_value = cur_value  # update the last value
        return bool(state)


@DocInheritor({'requires', 'evaluate', 'name'})
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

    def _compare(self, other):
        """
        Parameters
        ----------
        other: RelativeCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if not self._source_obj._compare(other._source_obj):
            return False
        if self._source_attr != other._source_attr:
            return False
        if self._relation != other._relation:
            return False
        if not self._threshold_obj._compare(other._threshold_obj):
            return False
        if self._threshold_attr != other._threshold_attr:
            return False
        return True

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
        return OrderedSet([self._source_obj, self._threshold_obj])

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
        return bool(state)


@DocInheritor({'requires', 'evaluate', 'backtrack'})
class OrCondition(ControlCondition):
    """Combine two WNTR Conditions with an OR.
    
    Parameters
    ----------
    cond1 : ControlCondition
        The first condition
    cond2 : ControlCondition
        The second condition

    """
    def __init__(self, cond1, cond2):
        self._condition_1 = cond1
        self._condition_2 = cond2

        if isinstance(cond1, TankLevelCondition):
            if cond1._relation is Comparison.eq:
                logger.warning('Using Comparison.eq with {0} will probably not work!'.format(type(cond1)))
                warnings.warn('Using Comparison.eq with {0} will probably not work!'.format(type(cond1)))

        if isinstance(cond2, TankLevelCondition):
            if cond2._relation is Comparison.eq:
                logger.warning('Using Comparison.eq with {0} will probably not work!'.format(type(cond2)))
                warnings.warn('Using Comparison.eq with {0} will probably not work!'.format(type(cond2)))

    def _reset(self):
        self._condition_1._reset()
        self._condition_2._reset()

    def _compare(self, other):
        """
        Parameters
        ----------
        other: OrCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if not self._condition_1._compare(other._condition_1):
            return False
        if not self._condition_2._compare(other._condition_2):
            return False
        return True

    def __str__(self):
        return " " + str(self._condition_1) + " OR " + str(self._condition_2) + " "

    def __repr__(self):
        return 'Or({}, {})'.format(repr(self._condition_1), repr(self._condition_2))

    def evaluate(self):
        return bool(self._condition_1) or bool(self._condition_2)

    @property
    def backtrack(self):
        return np.max([self._condition_1.backtrack, self._condition_2.backtrack])

    def requires(self):
        req = self._condition_1.requires()
        req.update(self._condition_2.requires())
        return req


@DocInheritor({'requires', 'evaluate', 'backtrack'})
class AndCondition(ControlCondition):
    """Combine two WNTR Conditions with an AND
    
    Parameters
    ----------
    cond1 : ControlCondition
        The first condition
    cond2 : ControlCondition
        The second condition
    """
    def __init__(self, cond1, cond2):
        self._condition_1 = cond1
        self._condition_2 = cond2

        if isinstance(cond1, TankLevelCondition):
            if cond1._relation is Comparison.eq:
                logger.warning('Using Comparison.eq with {0} will probably not work!'.format(type(cond1)))
                warnings.warn('Using Comparison.eq with {0} will probably not work!'.format(type(cond1)))

        if isinstance(cond2, TankLevelCondition):
            if cond2._relation is Comparison.eq:
                logger.warning('Using Comparison.eq with {0} will probably not work!'.format(type(cond2)))
                warnings.warn('Using Comparison.eq with {0} will probably not work!'.format(type(cond2)))

    def _reset(self):
        self._condition_1._reset()
        self._condition_2._reset()

    def _compare(self, other):
        """
        Parameters
        ----------
        other: OrCondition

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        if not self._condition_1._compare(other._condition_1):
            return False
        if not self._condition_2._compare(other._condition_2):
            return False
        return True

    def __str__(self):
        return " "+ str(self._condition_1) + " AND " + str(self._condition_2) + " "

    def __repr__(self):
        return 'And({}, {})'.format(repr(self._condition_1), repr(self._condition_2))

    def evaluate(self):
        return bool(self._condition_1) and bool(self._condition_2)

    @property
    def backtrack(self):
        return np.min([self._condition_1.backtrack, self._condition_2.backtrack])

    def requires(self):
        req = self._condition_1.requires()
        req.update(self._condition_2.requires())
        return req


class _CloseCVCondition(ControlCondition):
    Htol = 0.0001524
    Qtol = 2.83168e-6

    def __init__(self, wn, cv):
        self._cv = cv
        self._start_node = wn.get_node(cv.start_node)
        self._end_node = wn.get_node(cv.end_node)
        self._backtrack = 0

    def requires(self):
        return OrderedSet([self._cv, self._start_node, self._end_node])

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

    def __str__(self):
        s = '{0} head - {1} head < -{2} or {3} flow < {4}'.format(self._start_node.name, self._end_node.name, self.Htol, self._cv.name, -self.Qtol)
        return s


class _OpenCVCondition(ControlCondition):
    Htol = 0.0001524
    Qtol = 2.83168e-6

    def __init__(self, wn, cv):
        self._cv = cv
        self._start_node = wn.get_node(cv.start_node)
        self._end_node = wn.get_node(cv.end_node)
        self._backtrack = 0

    def requires(self):
        return OrderedSet([self._cv, self._start_node, self._end_node])

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

    def __str__(self):
        s = '{0} head - {1} head > {2} and {3} flow >= {4}'.format(self._start_node.name, self._end_node.name, self.Htol, self._cv.name, -self.Qtol)
        return s


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
        return OrderedSet([self._pump, self._start_node, self._end_node])

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        dh = self._end_node.head - self._start_node.head
        if dh > self.Hmax + self.Htol:
            return True
        return False

    def __str__(self):
        s = '{0} head - {1} head > {2:.4f}'.format(self._end_node.name, self._start_node.name, self.Hmax + self.Htol)
        return s


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
        return OrderedSet([self._pump, self._start_node, self._end_node])

    def evaluate(self):
        """
        If True is returned, the pump needs to be opened
        """
        dh = self._end_node.head - self._start_node.head
        if dh <= self.Hmax + self.Htol:
            return True
        return False

    def __str__(self):
        s = '{0} head - {1} head <= {2:.4f}'.format(self._end_node.name, self._start_node.name, self.Hmax + self.Htol)
        return s


class _CloseHeadPumpCondition(ControlCondition):
    """
    Prevents reverse flow in pumps.
    """
    _Htol = 0.0001524

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
        self._wn = wn

    def requires(self):
        return OrderedSet([self._pump, self._start_node, self._end_node])

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed_timeseries.at(self._wn.sim_time) != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        dh = self._end_node.head - self._start_node.head
        if dh > Hmax + self._Htol:
            return True
        return False

    def __str__(self):
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed_timeseries.at(self._wn.sim_time) != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        s = '{0} head - {1} head > {2:.4f}'.format(self._end_node.name, self._start_node.name, Hmax + self._Htol)
        return s


class _OpenHeadPumpCondition(ControlCondition):
    """
    Prevents reverse flow in pumps.
    """
    _Htol = 0.0001524

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
        self._wn = wn

    def requires(self):
        return OrderedSet([self._pump, self._start_node, self._end_node])

    def evaluate(self):
        """
        If True is returned, the pump needs to be closed
        """
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed_timeseries.at(self._wn.sim_time) != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        dh = self._end_node.head - self._start_node.head
        if dh <= Hmax + self._Htol:
            return True
        return False

    def __str__(self):
        a, b, c = self._pump.get_head_curve_coefficients()
        if self._pump.speed_timeseries.at(self._wn.sim_time) != 1.0:
            raise NotImplementedError('Pump speeds other than 1.0 are not yet supported.')
        Hmax = a
        s = '{0} head - {1} head <= {2:.4f}'.format(self._end_node.name, self._start_node.name, Hmax + self._Htol)
        return s


class _ClosePRVCondition(ControlCondition):
    _Qtol = 2.83168e-6

    def __init__(self, wn, prv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        prv: wntr.network.Valve
        """
        super(_ClosePRVCondition, self).__init__()
        self._prv = prv
        self._start_node = wn.get_node(self._prv.start_node)
        self._end_node = wn.get_node(self._prv.end_node)
        self._backtrack = 0

    def requires(self):
        return OrderedSet([self._prv])

    def evaluate(self):
        if self._prv._internal_status == LinkStatus.Active:
            if self._prv.flow < -self._Qtol:
                return True
            return False
        elif self._prv._internal_status == LinkStatus.Open:
            if self._prv.flow < -self._Qtol:
                return True
            return False
        elif self._prv._internal_status == LinkStatus.Closed:
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))

    def __str__(self):
        s = 'prv {0} needs to be closed'.format(self._prv.name)
        return s


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
        super(_OpenPRVCondition, self).__init__()
        self._prv = prv
        self._start_node = wn.get_node(self._prv.start_node)
        self._end_node = wn.get_node(self._prv.end_node)
        self._backtrack = 0
        self._r = 8.0 * self._prv.minor_loss / (9.81 * math.pi**2 * self._prv.diameter**4)

    def requires(self):
        return OrderedSet([self._prv, self._start_node, self._end_node])

    def evaluate(self):
        if self._prv._internal_status == LinkStatus.Active:
            if self._prv.flow < -self._Qtol:
                return False
            elif self._start_node.head < self._prv.setting + self._end_node.elevation + self._r * abs(self._prv.flow)**2 - self._Htol:
                return True
            return False
        elif self._prv._internal_status == LinkStatus.Open:
            return False
        elif self._prv._internal_status == LinkStatus.Closed:
            if self._start_node.head >= self._prv.setting + self._end_node.elevation + self._Htol and self._end_node.head < self._prv.setting + self._end_node.elevation - self._Htol:
                return False
            elif self._start_node.head < self._prv.setting + self._end_node.elevation - self._Htol and self._start_node.head > self._end_node.head + self._Htol:
                return True
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))

    def __str__(self):
        s = 'prv {0} needs to be open'.format(self._prv.name)
        return s


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
        self._r = 8.0 * self._prv.minor_loss / (9.81 * math.pi**2 * self._prv.diameter**4)

    def requires(self):
        return OrderedSet([self._prv, self._start_node, self._end_node])

    def evaluate(self):
        if self._prv._internal_status == LinkStatus.Active:
            return False
        elif self._prv._internal_status == LinkStatus.Open:
            if self._prv.flow < -self._Qtol:
                return False
            elif (self._end_node.head >= self._prv.setting + self._end_node.elevation + self._Htol):
                return True
            return False
        elif self._prv._internal_status == LinkStatus.Closed:
            if ((self._start_node.head >= self._prv.setting + self._end_node.elevation + self._Htol) and
                    (self._end_node.head < self._prv.setting + self._end_node.elevation - self._Htol)):
                return True
            return False
        else:
            raise RuntimeError('Unexpected PRV _internal_status for valve {0}: {1}.'.format(self._prv,
                                                                                            self._prv._internal_status))

    def __str__(self):
        s = 'prv {0} needs to be active'.format(self._prv.name)
        return s


class _ClosePSVCondition(ControlCondition):
    _Qtol = 2.83168e-6

    def __init__(self, wn, psv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        psv: wntr.network.Valve
        """
        super(_ClosePSVCondition, self).__init__()
        self._psv = psv
        self._start_node = wn.get_node(self._psv.start_node)
        self._end_node = wn.get_node(self._psv.end_node)
        self._backtrack = 0

    def requires(self):
        return OrderedSet([self._psv])

    def evaluate(self):
        if self._psv._internal_status == LinkStatus.Active:
            if self._psv.flow < -self._Qtol:
                return True
            return False
        elif self._psv._internal_status == LinkStatus.Open:
            if self._psv.flow < -self._Qtol:
                return True
            return False
        elif self._psv._internal_status == LinkStatus.Closed:
            return False
        else:
            raise RuntimeError('Unexpected PSV _internal_status for valve {0}: {1}.'.format(self._psv,
                                                                                            self._psv._internal_status))

    def __str__(self):
        s = 'psv {0} needs to be closed'.format(self._psv.name)
        return s


class _OpenPSVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, psv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        psv: wntr.network.Valve
        """
        super(_OpenPSVCondition, self).__init__()
        self._psv = psv
        self._start_node = wn.get_node(self._psv.start_node)
        self._end_node = wn.get_node(self._psv.end_node)
        self._backtrack = 0
        self._r = 8.0 * self._psv.minor_loss / (9.81 * math.pi**2 * self._psv.diameter**4)

    def requires(self):
        return OrderedSet([self._psv, self._start_node, self._end_node])

    def evaluate(self):
        setting = self._psv.setting + self._start_node.elevation
        if self._psv._internal_status == LinkStatus.Active:
            if self._psv.flow < -self._Qtol:
                return False
            elif self._end_node.head + self._r * abs(self._psv.flow)**2 > setting + self._Htol:
                return True
            return False
        elif self._psv._internal_status == LinkStatus.Open:
            return False
        elif self._psv._internal_status == LinkStatus.Closed:
            if ((self._end_node.head > setting + self._Htol) and
                    (self._start_node.head > self._end_node.head + self._Htol)):
                return True
            return False
        else:
            raise RuntimeError('Unexpected PSV _internal_status for valve {0}: {1}.'.format(self._psv,
                                                                                            self._psv._internal_status))

    def __str__(self):
        s = 'psv {0} needs to be open'.format(self._psv.name)
        return s


class _ActivePSVCondition(ControlCondition):
    _Qtol = 2.83168e-6
    _Htol = 0.0001524

    def __init__(self, wn, psv):
        """
        Parameters
        ----------
        wn: wntr.network.WaterNetworkModel
        psv: wntr.network.Valve
        """
        self._psv = psv
        self._start_node = wn.get_node(self._psv.start_node)
        self._end_node = wn.get_node(self._psv.end_node)
        self._backtrack = 0
        self._r = 8.0 * self._psv.minor_loss / (9.81 * math.pi**2 * self._psv.diameter**4)

    def requires(self):
        return OrderedSet([self._psv, self._start_node, self._end_node])

    def evaluate(self):
        setting = self._psv.setting + self._start_node.elevation
        if self._psv._internal_status == LinkStatus.Active:
            return False
        elif self._psv._internal_status == LinkStatus.Open:
            if self._psv.flow < -self._Qtol:
                return False
            elif (self._start_node.head < setting - self._Htol):
                return True
            return False
        elif self._psv._internal_status == LinkStatus.Closed:
            if ((self._end_node.head > setting + self._Htol) and
                    (self._start_node.head > self._end_node.head + self._Htol)):
                return False
            elif ((self._start_node.head >= setting + self._Htol) and
                  (self._start_node.head > self._end_node.head + self._Htol)):
                return True
            return False
        else:
            raise RuntimeError('Unexpected PSV _internal_status for valve {0}: {1}.'.format(self._psv,
                                                                                            self._psv._internal_status))

    def __str__(self):
        s = 'psv {0} needs to be active'.format(self._psv.name)
        return s


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
        return OrderedSet([self._fcv, self._start_node, self._end_node])

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
        return OrderedSet([self._fcv, self._start_node, self._end_node])

    def evaluate(self):
        if self._start_node.head - self._end_node.head < -self._Htol:
            return False
        elif self._fcv.flow < -self._Qtol:
            return False
        elif self._fcv._internal_status == LinkStatus.Open and self._fcv.flow >= self._fcv.setting + self._Qtol:
            return True
        else:
            return False


class BaseControlAction(six.with_metaclass(abc.ABCMeta, Subject)):
    """
    A base class for deriving new control actions. The control action is run by calling run_control_action.
    This class is not meant to be used directly. Derived classes must implement the run_control_action, requires,
    and target methods.
    """

    def __init__(self):
        super(BaseControlAction, self).__init__()
        self._value = None

    @abc.abstractmethod
    def run_control_action(self):
        """
        This method is called to run the corresponding control action.
        """
        pass

    @abc.abstractmethod
    def requires(self):
        """
        Returns a set of objects used to evaluate the control

        Returns
        -------
        req: OrderedSet
            The objects required to run the control action.
        """
        pass

    @abc.abstractmethod
    def target(self):
        """
        Returns a tuple (object, attribute) containing the object and attribute that the control action may change

        Returns
        -------
        target: tuple
            A tuple containing the target object and the attribute to be changed (target, attr).
        """
        pass

    def _compare(self, other):
        """
        Parameters
        ----------
        other: BaseControlAction

        Returns
        -------
        bool
        """
        if type(self) != type(other):
            return False
        target1, attr1 = self.target()
        target2, attr2 = other.target()
        val1 = self._value
        val2 = other._value
        if not target1._compare(target2):
            return False
        if attr1 != attr2:
            return False
        if type(val1) == float:
            if abs(val1 - val2) > 1e-10:
                return False
        else:
            if val1 != val2:
                return False
        return True


@DocInheritor({'requires', 'target', 'run_control_action'})
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
        super(ControlAction, self).__init__()
        if target_obj is None:
            raise ValueError('target_obj is None in ControlAction::__init__. A valid target_obj is needed.')
        if not hasattr(target_obj, attribute):
            raise ValueError('attribute given in ControlAction::__init__ is not valid for target_obj')

        self._target_obj = target_obj
        self._attribute = attribute
        self._value = value
        self._private_attribute = attribute
        if attribute == 'status':
            self._private_attribute = '_user_status'
        elif attribute == 'leak_status':
            self._private_attribute = '_leak_status'
        elif attribute == 'setting':
            self._private_attribute = '_setting'

    def requires(self):
        return OrderedSet([self._target_obj])

    def __repr__(self):
        return '<ControlAction: {}, {}, {}>'.format(str(self._target_obj), str(self._attribute), str(self._repr_value()))

    def __str__(self):
        return "{} {} {} IS {}".format(self._target_obj.link_type.upper(),
                                       self._target_obj.name,
                                       self._attribute.upper(),
                                       self._repr_value())

    def _repr_value(self):
        if self._attribute.lower() in ['status']:
            return LinkStatus(int(self._value)).name.upper()
        return self._value

    def run_control_action(self):
        setattr(self._target_obj, self._private_attribute, self._value)
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
        super(_InternalControlAction, self).__init__()
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
        return OrderedSet([self._target_obj])

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


#
# Control classes
#

class ControlBase(six.with_metaclass(abc.ABCMeta, object)):
    """
    This is the base class for all control objects. Control objects are used to check the conditions under which a
    ControlAction should be run. For example, if a pump is supposed to be turned on when the simulation time
    reaches 6 AM, the ControlAction would be "turn the pump on", and the ControlCondition would be "when the simulation
    reaches 6 AM".
    """

    def __init__(self):
        super().__init__()
        self._control_type = None
        self._condition = None
        self._priority = None

    @abc.abstractmethod
    def is_control_action_required(self):
        """
        This method is called to see if any action is required by this control object. This method returns a tuple
        that indicates if action is required (a bool) and a recommended time for the simulation to backup (in seconds
        as a positive int).

        Returns
        -------
        req: tuple
            A tuple (bool, int) indicating if an action should be run and how far to back up the simulation.
        """
        pass

    @abc.abstractmethod
    def run_control_action(self):
        """
        This method is called to run the control action after a call to IsControlActionRequired indicates that an
        action is required.
        """
        pass

    @abc.abstractmethod
    def requires(self):
        """
        Returns a set of objects required for this control.

        Returns
        -------
        required_objects: OrderedSet of object
        """
        return OrderedSet()

    @abc.abstractmethod
    def actions(self):
        """
        Returns a list of all actions used by this control.

        Returns
        -------
        act: list of BaseControlAction
        """
        pass

    def _control_type_str(self):
        if self._control_type is _ControlType.rule:
            return 'Rule'
        else:
            return 'Control'

    def _reset(self):
        self._condition._reset()

    @property
    def condition(self):
        return self._condition

    @property
    def priority(self):
        return self._priority

    def _compare(self, other):
        """
        Parameters
        ----------
        other: ControlBase

        Returns
        -------
        bool
        """
        ret = True
        msg = '_compare failed in ControlBase because '
        if self.priority != other.priority:
            ret = False
            msg += 'priorities were not equal'
        if self._control_type_str() != other._control_type_str():
            ret = False
            msg += '_control_type_strs were not equal'
        if not self.condition._compare(other.condition):
            ret = False
            msg += 'conditions were not equal'
        for action1, action2 in zip(self.actions(), other.actions()):
            if not action1._compare(action2):
                ret = False
                msg += 'actions were not equal'
                break
        if ret is False:
            print(msg)
        return ret


@DocInheritor({'is_control_action_required', 'run_control_action', 'requires', 'actions'})
class Rule(ControlBase):
    """
    A very general and flexible class for defining both controls rules.
    """
    def __init__(self, condition, then_actions, else_actions=None, priority=ControlPriority.medium, name=None):
        """
        Parameters
        ----------
        condition: ControlCondition
            The condition that should be used to determine when the actions need to be activated. When the condition
            evaluates to True, the then_actions are activated. When the condition evaluates to False, the else_actions
            are activated.
        then_actions: Iterable of ControlAction
            The actions that should be activated when the condition evaluates to True.
        else_actions: Iterable of ControlAction
            The actions that should be activated when the condition evaluates to False.
        priority: ControlPriority
            The priority of the control. Default is ControlPriority.medium
        name: str
            The name of the control
        """
        self.update_condition(condition)
        self.update_then_actions(then_actions)
        self.update_else_actions(else_actions)
        self._which = None
        self.update_priority(priority)
        self._name = name
        if self._name is None:
            self._name = ''
        self._control_type = _ControlType.rule

        if isinstance(condition, TankLevelCondition):
            if condition._relation is Comparison.eq:
                logger.warning('Using Comparison.eq with {0} will probably not work!'.format(type(condition)))
                warnings.warn('Using Comparison.eq with {0} will probably not work!'.format(type(condition)))

    def to_dict(self):
        ret = dict()
        if self._control_type == _ControlType.rule:
            ret['type'] = 'rule'
            ret['name'] = str(self._name)
            ret['condition'] = str(self._condition)
            ret['then_actions'] = [str(a) for a in self._then_actions]
            ret['else_actions'] = [str(a) for a in self._else_actions]
            ret['priority'] = int(self._priority)
        else:
            ret['type'] = 'simple'
            ret['condition'] = str(self._condition)
            ret['then_actions'] = [str(a) for a in self._then_actions]
        return ret

    @property
    def epanet_control_type(self):
        """
        The control type. Note that presolve and postsolve controls are both simple controls in Epanet.

        Returns
        -------
        control_type: _ControlType
        """
        return self._control_type
    
    def requires(self):
        req = self._condition.requires()
        for action in self._then_actions:
            req.update(action.requires())
        for action in self._else_actions:
            req.update(action.requires())
        return req

    def actions(self):
        return self._then_actions + self._else_actions

    @property
    def name(self):
        """
        A string representation of the Control.
        """
        if self._name is not None:
            return self._name
        else:
            return '/'.join(str(self).split())

    def __repr__(self):
        fmt = "<Control: '{}', {}, {}, {}, priority={}>"
        return fmt.format(self._name, repr(self._condition), repr(self._then_actions), repr(self._else_actions), self._priority)

    def __str__(self):
        text = 'IF {}'.format(str(self._condition))
        if self._then_actions is not None and len(self._then_actions) > 0:
            then_text = ' THEN '
            for ct, act in enumerate(self._then_actions):
                if ct == 0:
                    then_text += str(act)
                else:
                    then_text += ' AND {}'.format(str(act))
            text += then_text
        if self._else_actions is not None and len(self._else_actions) > 0:
            else_text = ' ELSE '
            for ct, act in enumerate(self._else_actions):
                if ct == 0:
                    else_text += str(act)
                else:
                    else_text += ' AND {}'.format(str(act))
            text += else_text
        if self._priority is not None and self._priority >= 0:
            text += ' PRIORITY {}'.format(self._priority)
        return text

    def is_control_action_required(self):
        do = self._condition.evaluate()
        back = self._condition.backtrack
        if do:
            self._which = 'then'
            return True, back
        elif not do and self._else_actions is not None and len(self._else_actions) > 0:
            self._which = 'else'
            return True, back
        else:
            return False, None

    def run_control_action(self):
        if self._which == 'then':
            for control_action in self._then_actions:
                control_action.run_control_action()
        elif self._which == 'else':
            for control_action in self._else_actions:
                control_action.run_control_action()
        else:
            raise RuntimeError('control actions called even though if-then statement was False')
    
    def update_condition(self, condition:ControlCondition):
        """Update the controls condition in place

        Parameters
        ----------
        condition : ControlCondition
            The new condition for this control to use

        Raises
        ------
        ValueError
            If the provided condition isn't a valid ControlCondition
        """
        try:
            logger.info(f"Replacing {self._condition} with {condition}")
        except AttributeError:
            # Occurs during intialisation
            pass
        if not isinstance(condition, ControlCondition):
            raise ValueError('The conditions argument must be a ControlCondition instance')
        self._condition = condition

    def update_then_actions(self, then_actions:Iterable[ControlAction]):
        """Update the controls then_actions in place

        Parameters
        ----------
        then_actions : Iterable[ControlAction]
            The new then_actions for this control to use
        """        
        try:
            logger.info(f"Replacing {self._then_actions} with {then_actions}")        
        except AttributeError:
            # Occurs during intialisation
            pass
        self._then_actions = _ensure_iterable(then_actions)

    def update_else_actions(self, else_actions:Iterable[ControlAction]):
        """Update the controls else_actions in place

        Parameters
        ----------
        else_actions : Iterable[ControlAction]
            The new else_actions for this control to use
        """
        try:
            logger.info(f"Replacing {self._else_actions} with {else_actions}")
        except AttributeError:
            # Occurs during intialisation
            pass
        self._else_actions = _ensure_iterable(else_actions)
    
    def update_priority(self, priority:ControlPriority):
        """Update the controls priority in place

        Parameters
        ----------
        priority : ControlPriority
            The new priority for this control to use
        """
        try:
            logger.info(f"Replacing {self._priority} with {priority}")
        except AttributeError:
            # Occurs during intialisation
            pass
        self._priority = priority


class Control(Rule):
    """
    A class for controls.
    """
    def __init__(self, condition, then_action: BaseControlAction, priority=ControlPriority.medium, name=None):
        """
        Parameters
        ----------
        condition: ControlCondition
            The condition that should be used to determine when the actions need to be activated. When the condition
            evaluates to True, the then_actions are activated. When the condition evaluates to False, the else_actions
            are activated.
        then_action: BaseControlAction
            The action that should be activated when the condition evaluates to True.
        priority: ControlPriority
            The priority of the control. Default is ControlPriority.medium
        name: str
            The name of the control
        """
        super().__init__(condition=condition, then_actions=then_action, priority=priority, name=name)
        if isinstance(condition, TankLevelCondition):
            self._control_type = _ControlType.pre_and_postsolve
        elif isinstance(condition, (TimeOfDayCondition, SimTimeCondition)):
            self._control_type = _ControlType.presolve
        else:
            self._control_type = _ControlType.postsolve
        
    @classmethod
    def _time_control(cls, wnm, run_at_time, time_flag, daily_flag, control_action, name=None):
        """
        This is a class method for creating simple time controls.

        Parameters
        ----------
        wnm: wntr.network.WaterNetworkModel
            The WaterNetworkModel instance this control will be added to.
        run_at_time: int
            The time to activate the control action.
        time_flag: str
            Options are 'SIM_TIME' and 'CLOCK_TIME'. SIM_TIME indicates that run_at_time is the time since the start
            of the simulation. CLOCK_TIME indicates that run_at_time is the time of day.
        daily_flag: bool
            If True, then the control will repeat every day.
        control_action: BaseControlAction
            The control action that should occur at run_at_time.
        name: str
            An optional name for the control.

        Returns
        -------
        ctrl: Control
        """
        if time_flag.upper() == 'SIM_TIME':
            condition = SimTimeCondition(model=wnm, relation=Comparison.eq, threshold=run_at_time, repeat=daily_flag,
                                         first_time=0)
        elif time_flag.upper() == 'CLOCK_TIME':
            condition = TimeOfDayCondition(model=wnm, relation=Comparison.eq, threshold=run_at_time, repeat=daily_flag,
                                           first_day=0)
        else:
            raise ValueError("time_flag not recognized; expected either 'sim_time' or 'clock_time'")

        control = Control(condition=condition, then_action=control_action)

        return control

    @classmethod
    def _conditional_control(cls, source_obj, source_attr, operation, threshold, control_action, name=None):
        """
        This is a class method for creating simple conditional controls.

        Parameters
        ----------
        source_obj: object
            The object whose source_attr attribute will be compared to threshold to determine if control_action
            needs activated.
        source_attr: str
            The attribute of source_obj to compare to threshold.
        operation: Comparison
            The comparison function used to compare the source_attr attribute of source_obj to threshold.
        threshold: any
            The threshold used in the comparison.
        control_action: ControlAction
            The control action that should occur when operation(getattr(source_obj, source_attr), threshold) is True.
        name: str
            An optional name for the control

        Returns
        -------
        ctrl: Control
        """
        condition = ValueCondition(source_obj=source_obj, source_attr=source_attr, relation=operation,
                                   threshold=threshold)
        control = Control(condition=condition, then_action=control_action)
        return control


class ControlChangeTracker(Observer):
    def __init__(self):
        self._actions = dict()
        self._previous_values: Dict[Any, Dict[Tuple[Any, str], Any]] = dict()  # {key: {(obj, attr): value}}
        self._changed: Dict[Any, MutableSet[Tuple[Any, str]]] = dict()  # {key: set of (obj, attr) that has been changed from _previous_values}

    def clear_all_reference_points(self):
        self._previous_values = dict()
        self._changed = dict()

    def _set_reference_point(self, key):
        self._previous_values[key] = dict()
        self._changed[key] = OrderedSet()

        for action in self._actions.keys():
            obj, attr = action.target()
            self._previous_values[key][(obj, attr)] = getattr(obj, attr)

    def set_reference_point(self, key):
        if key in self._previous_values:
            raise ValueError(f'The ControlChangeTracker already has reference point {key}')
        self._set_reference_point(key)

    def reset_reference_point(self, key):
        self._set_reference_point(key)

    def remove_reference_point(self, key):
        del self._previous_values[key]
        del self._changed[key]

    def update(self, subject):
        """
        The update method gets called when a subject (control action) is activated.

        Parameters
        -----------
        subject: BaseControlAction
        """
        obj_attr = subject.target()
        val = getattr(*obj_attr)
        for ref_point in self._previous_values.keys():
            if val == self._previous_values[ref_point][obj_attr]:
                self._changed[ref_point].discard(obj_attr)
            else:
                self._changed[ref_point].add(obj_attr)

    def register_control(self, control):
        """
        Register a control with the ControlManager

        Parameters
        ----------
        control: ControlBase
        """
        if len(self._previous_values) != 0:
            raise RuntimeError('Please call clear_reference_points() before registering more controls')
        for action in control.actions():
            if action not in self._actions:
                self._actions[action] = OrderedSet()
            self._actions[action].add(control)
            action.subscribe(self)

    def changes_made(self, ref_point):
        """
        Specifies if changes were made.

        Returns
        -------
        changes: bool
        """
        return len(self._changed[ref_point]) > 0

    def get_changes(self, ref_point):
        """
        A generator for iterating over the objects, attributes that were changed.

        Returns
        -------
        changes: tuple
            (object, attr)
        """
        for obj, attr in self._changed[ref_point]:
            yield obj, attr

    def deregister(self, control):
        """
        Deregister a control with the ControlManager

        Parameters
        ----------
        control: ControlBase
        """
        for action in control.actions():
            self._actions[action].discard(control)
            if len(self._actions[action]) == 0:
                action.unsubscribe(self)
                del self._actions[action]

                obj_attr = action.target()
                for ref_point in self._previous_values.keys():
                    self._previous_values[ref_point].pop(obj_attr)
                    self._changed[ref_point].discard(obj_attr)


class ControlChecker(object):
    def __init__(self):
        self._controls = OrderedSet()
        """OrderedSet of ControlBase"""

    def __iter__(self):
        return iter(self._controls)

    def register_control(self, control):
        """
        Register a control with the ControlManager

        Parameters
        ----------
        control: ControlBase
        """
        self._controls.add(control)

    def deregister(self, control):
        """
        Deregister a control with the ControlManager

        Parameters
        ----------
        control: ControlBase
        """
        self._controls.remove(control)

    def check(self):
        """
        Check which controls have actions that need activated.

        Returns
        -------
        controls_to_run: list of tuple
            The tuple is (ControlBase, backtrack)
        """
        controls_to_run = []
        for c in self._controls:
            do, back = c.is_control_action_required()
            if do:
                controls_to_run.append((c, back))
        return controls_to_run
