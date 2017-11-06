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
### Control Condition classes
#

class ControlCondition(object):
    """A base class for control conditions"""
    def __init__(self):
        self._backtrack = 0

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

    def evaluate(self):
        raise NotImplementedError('This is an abstract base class. It must be subclassed.')

    def __bool__(self):
        """Overload a boolean based on the evaluation."""
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
            return wntr.network.model.LinkStatus(int(value)).name
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


class SimpleNodeCondition(ControlCondition):
    """Conditional based only on the pressure of a junction or the level of a tank.
    
    Parameters
    ----------
    source_obj : wntr.network.model.Junction, wntr.network.model.Tank
        The junction or tank to use as a comparison
    relation : 'above', 'below', or function
        Accepts the words *above* or *below*, or accepts
        a function taking two arguments that returns a true or false. Usually a ``numpy.ufunc``
        such as ``np.less`` or ``np.greater_equal``
    threshold : float
        The pressure or tank level to use in the condition
    """
    def __init__(self, source_obj, relation, threshold):
        self._source_obj = source_obj
        if isinstance(source_obj, wntr.network.model.Tank):
            source_attr = 'level'
        elif isinstance(source_obj, wntr.network.model.Junction):
            source_attr = 'pressure'
        self._source_attr = source_attr
        self._relation = Comparison.parse(relation)
        if self._relation in [Comparison.eq, Comparison.ne, Comparison.le, Comparison.ge]:
            raise ValueError('Simple conditions can only take ABOVE (>) or BELOW (<)')
        self._threshold = self._parse_value(threshold)
        self._backtrack = 0

    @property
    def name(self):
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        else:
            obj = str(self._source_obj)

        return '/'.join([obj, self._source_attr, self._relation.symbol, self._threshold])

    def __repr__(self):
        return "${}".format(self.name)

    def __str__(self):
        typ = self._source_obj.__class__.__name__
        obj = str(self._source_obj)
        if hasattr(self._source_obj, 'name'):
            obj = self._source_obj.name
        att = self._source_attr
        rel = self._relation.text
        if att == 'pressure':
            uni = 'kPa'
        else:
            uni = 'm'
        return '{} {} {} {} {:.6g} {}'.format(obj, typ, att, rel, self._threshold, uni)

    def evaluate(self):
        cur_value = getattr(self._source_obj, self._source_attr)
        thresh_value = self._threshold
        relation = self._relation
        if np.isnan(self._threshold):
            relation = np.greater
            thresh_value = 0.0
        state = relation(cur_value, thresh_value)
        return state

    def requires(self):
        return [self._source_obj]


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
        return "<ValueCondition: {}, {}, {}, {}>".format(repr(self._source_obj),
                                                       repr(self._source_attr),
                                                       repr(self._relation.symbol),
                                                       repr(self._threshold))

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
        return "RelativeCondition({}, {}, {}, {}, {})".format(repr(self._source_obj),
                                                              repr(self._source_attr),
                                                              repr(self._relation),
                                                              repr(self._threshold_obj),
                                                              repr(self._threshold_attr))

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

#
### Control Action classes
#


class BaseControlAction(object):
    """
    A base class for deriving new control actions. The control action is run by calling RunControlAction
    This class is not meant to be used directly. Derived classes must implement the RunControlActionImpl method.
    """
    def __init__(self):
        pass

    def RunControlAction(self, control_name):
        """
        This method is called to run the corresponding control action.
        """
        return self._RunControlActionImpl(control_name)

    def _RunControlActionImpl(self):
        """
        Implements the specific action that will be run when RunControlAction is called. This method should be
        overridden in derived classes.
        """
        raise NotImplementedError('_RunActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')

    def requires(self):
        """Returns a list of objects used to evaluate the control"""
        return []

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

        self._target_obj_ref = target_obj
        self._attribute = attribute
        self._value = value

        #if (isinstance(target_obj, wntr.network.Valve) or (isinstance(target_obj, wntr.network.Pipe) and target_obj.cv)) and attribute=='status':
        #    raise ValueError('You may not add controls to valves or pipes with check valves.')

    def requires(self):
        return [self._target_obj_ref]

    def __repr__(self):
        return '<ControlAction: {}, {}, {}>'.format(repr(self._target_obj_ref), repr(self._attribute), repr(self._repr_value()))

    def __str__(self):
        return "set {}('{}').{} to {}".format(self._target_obj_ref.__class__.__name__,
                                       self._target_obj_ref.name,
                                       self._attribute,
                                       self._repr_value())

    def _repr_value(self):
        if self._attribute.lower() in ['status']:
            return wntr.network.model.LinkStatus(int(self._value)).name
        return self._value

    def __eq__(self, other):
        if self._target_obj_ref == other._target_obj_ref and \
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

    def _RunControlActionImpl(self, control_name):
        """
        This method overrides the corresponding method from the BaseControlAction class. Here, it changes
        target_obj.attribute to the provided value.
        This method should not be called directly. Use RunControlAction of the ControlAction base class instead.
        """
        target = self._target_obj_ref
        if target is None:
            raise ValueError('target is None inside TargetAttribureControlAction::_RunControlActionImpl.' +
                             'This may be because a target_obj was added, but later the object itself was deleted.')
        if not hasattr(target, self._attribute):
            raise ValueError('attribute specified in ControlAction is not valid for targe_obj')

        orig_value = getattr(target, self._attribute)
        if orig_value == self._value:
            return False, None, None
        else:
            #logger.debug('control {0} setting {1} {2} to {3}'.format(control_name, target.name(),self._attribute,self._value))
            setattr(target, self._attribute, self._value)
            return True, (target, self._attribute), orig_value

#
### Control classes
#

class Control(object):
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
    def __init__(self):
        pass

    def IsControlActionRequired(self, wnm, presolve_flag):
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
        return self._IsControlActionRequiredImpl(wnm, presolve_flag)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This method should be implemented in derived Control classes as the main implementation of
        IsControlActionRequired.
        The derived classes that override this method should return a tuple that indicates if action is required (a
        bool) and a recommended time for the simulation to backup (in seconds as a positive int).
        This method should not be called directly. Use IsControlActionRequired instead. For more details see
        documentation for IsControlActionRequired.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated.
        presolve_flag : bool
            This is true if we are calling before the solve, and false if we are calling after the solve (within the
            current timestep).
        """
        raise NotImplementedError('_IsControlActionRequiredImpl is not implemented. '
                                  'This method must be implemented in any '
                                  ' class derived from Control.')

    def RunControlAction(self, wnm, priority):
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
        return self._RunControlActionImpl(wnm, priority)

    def _RunControlActionImpl(self, wnm, priority):
        """
        This is the method that should be overridden in derived classes to implement the action of firing the control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        raise NotImplementedError('_RunControlActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')

    def requires(self):
        """Returns a list of objects required to evaluate this control"""
        return []

class IfThenElseControl(Control):
    """If-Then[-Else] contol
    """
    def __init__(self, condition, then_actions, else_actions=None, priority=None, name=None):
        if not isinstance(condition, ControlCondition):
            raise ValueError('The conditions argument must be a ControlCondition instance')
        self._condition = condition
        if not isinstance(then_actions, list) and then_actions is not None:
            self._then_actions = [then_actions]
        else:
            self._then_actions = then_actions
        if else_actions is not None:
            if not isinstance(else_actions, list):
                self._else_actions = [else_actions]
            else:
                self._else_actions = else_actions
        else:
            self._else_actions = None
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

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
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
            return (True, back)
        elif not do and self._else_actions is not None and len(self._else_actions) > 0:
            self._which = 'else'
            return (True, back)
        else:
            return (False, None)
        return None

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        if self._then_actions is None:
            raise ValueError('_control_action is None inside TimeControl')

        if self._priority != priority:
            return False, None, None
        flags = []
        tuples = []
        origins = []
        if self._which == 'then':
            for control_action in self._then_actions:
                change_flag, change_tuple, orig_value = control_action.RunControlAction(self.name)
                flags.append(change_flag)
                tuples.append(change_tuple)
                origins.append(orig_value)
        elif self._which == 'else':
            for control_action in self._else_actions:
                change_flag, change_tuple, orig_value = control_action.RunControlAction(self.name)
                flags.append(change_flag)
                tuples.append(change_tuple)
                origins.append(orig_value)
        else:
            raise RuntimeError('control actions called even though if-then statement was False')
        return np.max(flags), tuples, origins



class TimeControl(Control):
    """
    A class for creating time controls to run a control action at a particular
    time. At the specified time, control_action will be run/activated.
    
    Parameters
    ----------
    wnm : WaterNetworkModel
        The instance of the WaterNetworkModel class that is being simulated/modified.
    run_at_time : int
        Time (in seconds) when the control_action should be run.
    time_flag : string
        Options include SIM_TIME and SHIFTED_TIME
        * SIM_TIME indicates that the value of run_at_time is in seconds since
          the start of the simulation
        * SHIFTED_TIME indicates that the value of run_at_time is shifted by the
          start time of the simulations. That is, run_at_time is in seconds since
          12 AM on the first day of the simulation. Therefore, 7200 refers to 2:00 AM
          regardless of the start time of the simulation.
    daily_flag : bool
        * False indicates that control will execute once when time is first encountered
        * True indicates that control will execute at the same time daily
    control_action : An object derived from BaseControlAction
        Examples: ControlAction
        This is the actual change that will occur at the specified time.
    """

    def __init__(self, wnm, run_at_time, time_flag, daily_flag, control_action):
        self.name = 'blah'

        if isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.opened:
            self._priority = 0
        elif isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.closed:
            self._priority = 3
        else:
            self._priority = 0

        self._run_at_time = run_at_time
        self._time_flag = time_flag
        if time_flag != 'SIM_TIME' and time_flag != 'SHIFTED_TIME':
            raise ValueError('In TimeControl::__init__, time_flag must be "SIM_TIME" or "SHIFTED_TIME"')

        self._daily_flag = daily_flag
        self._control_action = control_action

        if daily_flag and run_at_time > 24*3600:
            raise ValueError('In TimeControl, a daily control was requested, however, the time passed in was not between 0 and 24*3600')

        if time_flag == 'SIM_TIME' and self._run_at_time < wnm.sim_time:
            raise RuntimeError('You cannot create a time control that should be activated before the start of the simulation.')

        if time_flag == 'SHIFTED_TIME' and self._run_at_time < wnm._shifted_time:
            self._run_at_time += 24*3600

    def requires(self):
        req = self._control_action.requires()
        return req

    def __str__(self):
        if self._time_flag == 'SIM_TIME':
            fmt = 'LINK {} {} AT TIME {}'
            tm = ControlCondition._sec_to_hours_min_sec(self._run_at_time)
        else:
            fmt = 'LINK {} {} AT CLOCKTIME {}'
            tm = ControlCondition._sec_to_clock(self._run_at_time)
        return fmt.format(self._control_action._target_obj_ref.name,
                          self._control_action._repr_value(),
                          tm)

    def __repr__(self):
        fmt = '<TimeControl: model, {}, {}, {}, {}>'
        return fmt.format(repr(self._run_at_time), repr(self._time_flag), repr(self._daily_flag), repr(self._control_action))

    def __eq__(self, other):
        if self._run_at_time      == other._run_at_time      and \
           self.name            == other.name            and \
           self._time_flag      == other._time_flag      and \
           self._daily_flag     == other._daily_flag     and \
           self._priority       == other._priority       and \
           self._control_action == other._control_action:
            return True
        return False

    def __hash__(self):
        return id(self)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
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
        if not presolve_flag:
            return (False, None)

        if self._time_flag == 'SIM_TIME':
            if wnm._prev_sim_time < self._run_at_time and self._run_at_time <= wnm.sim_time:
                return (True, int(wnm.sim_time - self._run_at_time))
        elif self._time_flag == 'SHIFTED_TIME':
            if wnm._prev_shifted_time < self._run_at_time and self._run_at_time <= wnm.shifted_time:
                return (True, int(round(wnm._shifted_time - self._run_at_time)))

        return (False, None)

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        if self._control_action is None:
            raise ValueError('_control_action is None inside TimeControl')

        if self._priority != priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.RunControlAction(self.name)
        if self._daily_flag:
            self._run_at_time += 24*3600
        return change_flag, change_tuple, orig_value


class ConditionalControl(Control):
    """
    A class for creating controls that run when a specified condition is satisfied. The control_action is
    run/activated when the operation evaluated on the source object/attribute and the threshold is True.
    
    Parameters
    ----------
    source : tuple
        A two-tuple. The first value should be an object (such as a Junction, Tank, Reservoir, Pipe, Pump, Valve,
        WaterNetworkModel, etc.). The second value should be an attribute of the object.
    operation : numpy comparison method
        Examples: numpy.greater, numpy.less_equal
    threshold : float
        A value to compare the source object attribute against
    control_action : An object derived from BaseControlAction
        Examples: ControlAction
        This object defines the actual change that will occur when the specified condition is satisfied.
    """

    def __init__(self, source, operation, threshold, control_action):
        self.name = 'blah'

        if isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.opened:
            self._priority = 0
        elif isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.closed:
            self._priority = 3
        else:
            self._priority = 0

        self._partial_step_for_tanks = True
        self._source_obj = source[0]
        self._source_attr = source[1]
        self._operation = operation
        self._control_action = control_action
        self._threshold = threshold

        if not isinstance(source,tuple):
            raise ValueError('source must be a tuple, (source_object, source_attribute).')
        if not isinstance(threshold,float):
            raise ValueError('threshold must be a float.')

    def requires(self):
        req = [self._source_obj] + self._control_action.requires()
        return req

    def __str__(self):
        fmt = 'LINK {} {} IF NODE {} {} {}'
        return fmt.format(self._control_action._target_obj_ref.name,
                          self._control_action._repr_value(),
                          self._source_obj.name,
                          Comparison.parse(self._operation).text,
                          self._threshold)

    def __repr__(self):
        fmt = '<ConditionalControl: {}, {}), {}, {}, {}>'
        return fmt.format(repr(self._source_obj), repr(self._source_attr), repr(self._operation), repr(self._threshold), repr(self._control_action))

    def __eq__(self, other):
        if self._priority               == other._priority               and \
           self.name                    == other.name                    and \
           self._partial_step_for_tanks == other._partial_step_for_tanks and \
           self._source_obj             == other._source_obj             and \
           self._source_attr            == other._source_attr            and \
           self._operation              == other._operation              and \
           self._control_action         == other._control_action         and \
           abs(self._threshold           - other._threshold)<1e-10:
            return True
        return False

    def __hash__(self):
        return id(self)


#    def to_inp_string(self, flowunit):
#        link_name = self._control_action._target_obj_ref.name()
#        action = 'OPEN'
#        if self._control_action._attribute == 'status':
#            if self._control_action._value == 1:
#                action = 'OPEN'
#            else:
#                action = 'CLOSED'
#        else:
#            action = str(self._control_action._value)
#        target_name = self._source_obj.name()
#        compare = 'ABOVE'
#        if self._relation is np.less:
#            compare = 'BELOW'
#        threshold = convert('Hydraulic Head',flowunit,self._threshold-self._source_obj.elevation,False)
#        return 'Link %s %s IF Node %s %s %s'%(link_name, action, target_name, compare, threshold)


    # @classmethod
    # def WithTarget(self, source, operation, threshold, target_obj, target_attribute, target_value):
    #     ca = ControlAction(target_obj, target_attribute, target_value)
    #     return ConditionalControl(source, operation, threshold, ca)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
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
        if type(self._source_obj)==wntr.network.Tank and self._source_attr=='level' and wnm.sim_time!=0 and self._partial_step_for_tanks:
            if presolve_flag:
                val = getattr(self._source_obj,self._source_attr)
                q_net = self._source_obj._prev_demand
                delta_h = 4.0*q_net*(wnm.sim_time-wnm._prev_sim_time)/(math.pi*self._source_obj.diameter**2)
                next_val = val+delta_h
                if self._operation(next_val, self._threshold) and self._operation(val, self._threshold):
                    return (False, None)
                if self._operation(next_val, self._threshold):
                    #if self._source_obj.name()=='TANK-3352':
                        #print 'threshold for tank 3352 control is ',self._threshold

                    m = (next_val-val)/(wnm.sim_time-wnm._prev_sim_time)
                    b = next_val - m*wnm.sim_time
                    new_t = (self._threshold - b)/m
                    #print 'new time = ',new_t
                    return (True, int(math.floor(wnm.sim_time-new_t)))
                else:
                    return (False, None)
            else:
                val = getattr(self._source_obj,self._source_attr)
                if self._operation(val, self._threshold):
                    return (True, 0)
                else:
                    return (False, None)
        elif type(self._source_obj==wntr.network.Tank) and self._source_attr=='level' and wnm.sim_time==0 and self._partial_step_for_tanks:
            if presolve_flag:
                val = getattr(self._source_obj, self._source_attr)
                if self._operation(val, self._threshold):
                    return (True, 0)
                else:
                    return (False, None)
            else:
                return (False, None)
        elif presolve_flag:
            return (False, None)
        else:
            val = getattr(self._source_obj, self._source_attr)
            if self._operation(val, self._threshold):
                return (True, 0)
            else:
                return (False, None)

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value

class _MultiConditionalControl(Control):
    """
    TODO:  Make this class private -- used specifically for internal (valve) controls, not
    RULES or CONTROLS section.
    A class for creating controls that run only when a set of specified conditions are all satisfied.
    
    Parameters
    ----------
    source : list of two-tuples
        A list of two-tuples. The first value of each tuple should be an object (e.g., Junction, Tank, Reservoir,
        Pipe, Pump, Valve, WaterNetworkModel, etc.). The second value of each tuple should be an attribute of the
        object.
    operation : list of numpy comparison methods
        Examples: [numpy.greater, numpy.greater, numpy.less_equal]
    threshold : list of floats or two-tuples
        Examples: [3.8, (junction1,'head'), (tank3,'head'), 0.5]
    control_action : An object derived from BaseControlAction
        Examples: ControlAction
        This object defines the actual change that will occur when all specified conditions are satisfied.
    """

    def __init__(self, source, operation, threshold, control_action):
        self.name = 'blah'
        self._priority = 0
        self._source = source
        self._relation = operation
        self._control_action = control_action
        self._threshold = threshold

        if not isinstance(source,list):
            raise ValueError('source must be a list of tuples, (source_object, source_attribute).')
        if not isinstance(operation,list):
            raise ValueError('operation must be a list numpy operations (e.g.,numpy.greater).')
        if not isinstance(threshold,list):
            raise ValueError('threshold must be a list of floats or tuples (threshold_object, threshold_attribute).')
        if len(source)!=len(operation):
            raise ValueError('The length of the source list must equal the length of the operation list.')
        if len(source)!=len(threshold):
            raise ValueError('The length of the source list must equal the length of the threshold list.')

    def requires(self):
        req = []
        for source, attr in self._source:
            req += [source]
        req += self._control_action.requires()
        return req

    def __eq__(self, other):
        if self._control_action == other._control_action and \
           self.name            == other.name            and \
           self._priority       == other._priority       and \
           self._relation      == other._relation:
            for point1, point2 in zip(self._threshold, other._threshold):
                if type(point1) == tuple:
                    if not point1 == point2:
                        return False
                elif not abs(point1-point2)<1e-8:
                    return False
            return True
        else:
            return False

    def __hash__(self):
        return id(self)

    # @classmethod
    # def WithTarget(self, source_obj, source_attribute, source_attribute_prev, operation, threshold, target_obj, target_attribute, target_value):
    #     ca = ControlAction(target_obj, target_attribute, target_value)
    #     return ConditionalControl(source_obj, source_attribute, source_attribute_prev, operation, threshold, ca)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
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
        if presolve_flag:
            return (False, None)

        action_required = True
        for ndx in range(len(self._source)):
            src_obj = self._source[ndx][0]
            src_attr = self._source[ndx][1]
            src_val = getattr(src_obj, src_attr)
            oper = self._relation[ndx]
            if not isinstance(self._threshold[ndx],tuple):
                threshold_val = self._threshold[ndx]
            else:
                threshold_obj = self._threshold[ndx][0]
                threshold_attr = self._threshold[ndx][1]
                threshold_val = getattr(threshold_obj, threshold_attr)

            if src_val is None or not oper(src_val, threshold_val):
                action_required = False
                break

        if action_required:
            return (True, 0)
        else:
            return (False, None)

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.
        
        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only run if priority == self._priority.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value

### Valve control classes

class _CheckValveHeadControl(Control):
    """
    """
    def __init__(self, wnm, cv, operation, threshold, control_action):
        self.name = 'blah'
        self._priority = 3
        self._cv = cv
        self._relation = operation
        self._threshold = threshold
        self._control_action = control_action
        self._start_node_name = self._cv.start_node
        self._end_node_name = self._cv.end_node
        self._start_node = wnm.get_node(self._start_node_name)
        self._end_node = wnm.get_node(self._end_node_name)
        self._pump_A = None

        if isinstance(self._cv,wntr.network.Pump):
            if self._cv.info_type == 'HEAD':
                A,B,C = self._cv.get_head_curve_coefficients()
                self._pump_A = A

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        if presolve_flag:
            return (False, None)

        if self._pump_A is not None:
            headloss = self._start_node.head + self._pump_A - self._end_node.head
        elif isinstance(self._cv,wntr.network.Pump):
            headloss = self._end_node.head - self._start_node.head
        else:
            headloss = self._start_node.head - self._end_node.head
        if self._relation(headloss, self._threshold):
            return (True, 0)
        return (False, None)

    def _RunControlActionImpl(self, wnm, priority):
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value

class _PRVControl(Control):
    """
    """
    def __init__(self, wnm, valve, Htol, Qtol, close_control_action, open_control_action, active_control_action):
        self.name = 'blah'
        self._priority = 3
        self._valve = valve
        self._Htol = Htol
        self._Qtol = Qtol
        self._close_control_action = close_control_action
        self._open_control_action = open_control_action
        self._active_control_action = active_control_action
        self._action_to_run = None
        self._start_node_name = valve.start_node
        self._end_node_name = valve.end_node
        self._start_node = wnm.get_node(self._start_node_name)
        self._end_node = wnm.get_node(self._end_node_name)
        self._resistance_coefficient = 0.0826*0.02*self._valve.diameter**(-5)*self._valve.diameter*2.0

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if presolve_flag:
            return (False, None)

        head_setting = self._valve.setting + self._end_node.elevation

        if self._valve._status == wntr.network.LinkStatus.active:
            if self._valve.flow < -self._Qtol:
                self._action_to_run = self._close_control_action
                return (True, 0)
            Hl = self._resistance_coefficient*abs(self._valve.flow)**2
            if self._start_node.head < head_setting + Hl - self._Htol:
                self._action_to_run = self._open_control_action
                return (True, 0)
            return (False, None)
        elif self._valve._status == wntr.network.LinkStatus.opened:
            if self._valve.flow < -self._Qtol:
                self._action_to_run = self._close_control_action
                return (True, 0)
            Hl = self._resistance_coefficient*abs(self._valve.flow)**2
            if self._start_node.head > head_setting + Hl + self._Htol:
                self._action_to_run = self._active_control_action
                return (True, 0)
            return (False, None)
        elif self._valve._status == wntr.network.LinkStatus.closed:
            if self._start_node.head > self._end_node.head + self._Htol and self._start_node.head < head_setting - self._Htol:
                self._action_to_run = self._open_control_action
                return (True, 0)
            if self._start_node.head > self._end_node.head + self._Htol and self._end_node.head < head_setting - self._Htol:
                self._action_to_run = self._active_control_action
                return (True, 0)
            return (False, None)

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._action_to_run.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value


class _FCVControl(Control):
    """
    Parameters
    ----------
    wnm: wntr.network.WaterNetworkModel
    valve: wntr.network.Valve
    Qtol: float
    open_control_action: ControlAction
    active_control_action: ControlAction
    """

    def __init__(self, wnm, valve, Htol, open_control_action, active_control_action):
        self.name = 'fcv'
        self._priority = 3
        self._valve = valve
        self._Htol = Htol
        self._open_control_action = open_control_action
        self._active_control_action = active_control_action
        self._action_to_run = None
        self._start_node_name = valve.start_node
        self._end_node_name = valve.end_node
        self._start_node = wnm.get_node(self._start_node_name)
        self._end_node = wnm.get_node(self._end_node_name)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if presolve_flag:
            if self._valve._status == wntr.network.LinkStatus.Active:
                self._action_to_run = self._open_control_action
                return True, 0
            return False, None

        if self._valve._status == wntr.network.LinkStatus.Active:
            actual_headloss = self._start_node.head - self._end_node.head
            if actual_headloss < 0: # flow should be negative
                self._action_to_run = self._open_control_action
                return True, 0
            headloss_if_open = (8.0 * self._valve.minor_loss / (9.81 * math.pi**2 * self._valve.diameter**4) *
                                self._valve.flow ** 2)
            if actual_headloss + self._Htol < headloss_if_open:
                self._action_to_run = self._open_control_action
                return True, 0
            return False, None
        elif self._valve._status == wntr.network.LinkStatus.Opened:
            if self._valve.flow > self._valve.setting:
                self._action_to_run = self._active_control_action
                return True, 0
            return False, None
        elif self._valve._status == wntr.network.LinkStatus.Closed:
            return False, None
        else:
            raise ValueError('unexpected _status for valve: \n\tValve: {0}\n\t_status: {1}'.format(self._valve,
                                                                                                   self._valve._status))

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._action_to_run.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value


class _ValveNewSettingControl(Control):
    """
    This is a control to change the valve status to active when a new setting is given to the valve (see page 73 of
    the Epanet2 user manual).

    Parameters
    ----------
    wnm: wntr.network.WaterNetworkModel
    valve: wntr.network.Valve
    Qtol: float
    open_control_action: ControlAction
    active_control_action: ControlAction
    """

    def __init__(self, wnm, valve):
        self.name = 'new_valve_setting_makes_status_active'
        self._priority = 1
        self._valve = valve
        valve._prev_setting = valve.setting
        self._active_control_action = ControlAction(valve, 'status', wntr.network.LinkStatus.Active)
        self._action_to_run = self._active_control_action

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if presolve_flag:
            return False, None

        if self._valve.status == wntr.network.LinkStatus.Closed:
            if self._valve._prev_setting != self._valve.setting:
                self._action_to_run = self._active_control_action
                return True, 0
            return False, None
        elif self._valve.status == wntr.network.LinkStatus.Opened:
            if self._valve._prev_setting != self._valve.setting:
                self._action_to_run = self._active_control_action
                return True, 0
            return False, None
        elif self._valve.status == wntr.network.LinkStatus.Active:
            return False, None
        else:
            raise ValueError('unexpected status for valve: \n\tValve: {0}\n\t_status: {1}'.format(self._valve,
                                                                                                   self._valve.status))

    def _RunControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._action_to_run.RunControlAction(self.name)
        return change_flag, change_tuple, orig_value

### Logger

class ControlLogger(object):
    def __init__(self):
        self.changed_objects = {}  # obj_name: object
        self.changed_attributes = {}  # obj_name: attribute

    def add(self, obj, attr):
        if obj.name in self.changed_objects:
            self.changed_attributes[obj.name].append(attr)
        else:
            self.changed_objects[obj.name] = obj
            self.changed_attributes[obj.name] = [attr]

    def reset(self):
        self.changed_objects = {}
        self.changed_attributes = {}
