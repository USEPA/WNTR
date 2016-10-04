"""
Classes and methods used for specifying controls and control actions
that may modify parameters in the network during simulation.
"""
import wntr
import weakref
import numpy as np
import math
from wntr.utils import convert
import logging

logger = logging.getLogger('wntr.network.NetworkControls')

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


class BaseControlAction(object):
    """ 
    A base class for deriving new control actions. The control action is fired by calling FireControlAction

    This class is not meant to be used directly. Derived classes must implement the FireControlActionImpl method.
    """
    def __init__(self):
        pass

    def FireControlAction(self, control_name):
        """ 
        This method is called to fire the corresponding control action.
        """
        return self._FireControlActionImpl(control_name)

    def _FireControlActionImpl(self):
        """
        Implements the specific action that will be fired when FireControlAction is called. This method should be
        overridden in derived classes.
        """
        raise NotImplementedError('_FireActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')

class ControlAction(BaseControlAction):
    """
    A general class for specifying a control action that simply modifies the attribute of an object (target).

    Parameters
    ----------
    target_obj : object
        The object whose attribute will be changed when the control fires.

    attribute : string
        The attribute that will be changed on the target_obj when the control fires.

    value : any
        The new value for target_obj.attribute when the control fires.
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
                    
                
           

    def _FireControlActionImpl(self, control_name):
        """
        This method overrides the corresponding method from the BaseControlAction class. Here, it changes
        target_obj.attribute to the provided value.

        This method should not be called directly. Use FireControlAction of the ControlAction base class instead.
        """
        target = self._target_obj_ref
        if target is None:
            raise ValueError('target is None inside TargetAttribureControlAction::_FireControlActionImpl.' +
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

class Control(object):
    """
    This is the base class for all control objects. Control objects are used to check the conditions under which a
    ControlAction should be fired. For example, if a pump is supposed to be turned on when the simulation time
    reaches 6 AM, the ControlAction would be "turn the pump on", and the Control would be "when the simulation
    reaches 6 AM".

    From an implementation standpoint, derived Control classes implement a particular mechanism for monitoring state
    (e.g. checking the simulation time to see if a change should be made). Then, they typically call FireControlAction
    on a derived ControlAction class.

    New Control classes (classes derived from Control) must implement the following methods:

    - _IsControlActionRequiredImpl(self, wnm, presolve_flag)
    - _FireControlActionImpl(self, wnm, priority)

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

    def FireControlAction(self, wnm, priority):
        """
        This method is called to fire the control action after a call to IsControlActionRequired indicates that an
        action is required.

        Note: Derived classes should not override this method, but should override _FireControlActionImpl instead.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only fired if priority == self._priority.
        """
        return self._FireControlActionImpl(wnm, priority)

    def _FireControlActionImpl(self, wnm, priority):
        """
        This is the method that should be overridden in derived classes to implement the action of firing the control.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only fired if priority == self._priority.
        """
        raise NotImplementedError('_FireControlActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')


class TimeControl(Control):
    """
    A class for creating time controls to fire a control action at a particular time. At the specified time,
    control_action will be fired/activated.

    Parameters
    ----------
    wnm : WaterNetworkModel
        The instance of the WaterNetworkModel class that is being simulated/modified.

    fire_time : int
        time (in seconds) when the control_action should be fired.

    time_flag : string, ('SIM_TIME', 'SHIFTED_TIME')

        SIM_TIME: indicates that the value of fire_time is in seconds since the start of the simulation

        SHIFTED_TIME: indicates that the value of fire_time is shifted by the start time of the simulations. That is,
            fire_time is in seconds since 12 AM on the first day of the simulation. Therefore, 7200 refers to 2:00 AM
            regardless of the start time of the simulation.

    daily_flag : bool
        False : control will execute once when time is first encountered
        True : control will execute at the same time daily

    control_action : An object derived from BaseControlAction
        Examples: ControlAction
        This is the actual change that will occur at the specified time.

    Examples
    --------
    >>> pipe = wn.get_link('pipe8')
    >>> action = ControlAction(pipe, 'status', wntr.network.LinkStatus.opened)
    >>> control = TimeControl(wn, 3652, 'SIM_TIME', False, action)
    >>> wn.add_control('control_name', control)

    In this case, pipe8 will be opened 1 hour and 52 seconds after the start of the simulation.
    """

    def __init__(self, wnm, fire_time, time_flag, daily_flag, control_action):
        self.name = 'blah'

        if isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.opened:
            self._priority = 0
        elif isinstance(control_action._target_obj_ref,wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.closed:
            self._priority = 3
        else:
            self._priority = 0

        self._fire_time = fire_time
        self._time_flag = time_flag
        if time_flag != 'SIM_TIME' and time_flag != 'SHIFTED_TIME':
            raise ValueError('In TimeControl::__init__, time_flag must be "SIM_TIME" or "SHIFTED_TIME"')

        self._daily_flag = daily_flag
        self._control_action = control_action

        if daily_flag and fire_time > 24*3600:
            raise ValueError('In TimeControl, a daily control was requested, however, the time passed in was not between 0 and 24*3600')

        if time_flag == 'SIM_TIME' and self._fire_time < wnm.sim_time:
            raise RuntimeError('You cannot create a time control that should be activated before the start of the simulation.')

        if time_flag == 'SHIFTED_TIME' and self._fire_time < wnm.shifted_time():
            self._fire_time += 24*3600

    def __eq__(self, other):
        if self._fire_time      == other._fire_time      and \
           self.name            == other.name            and \
           self._time_flag      == other._time_flag      and \
           self._daily_flag     == other._daily_flag     and \
           self._priority       == other._priority       and \
           self._control_action == other._control_action:
            return True
        return False

    def to_inp_string(self):
        link_name = self._control_action._target_obj_ref.name()
        action = 'OPEN'
        if self._control_action._attribute == 'status':
            if self._control_action._value == 1:
                action = 'OPEN'
            else:
                action = 'CLOSED'
        else:
            action = str(self._control_action._value)
        compare = 'TIME'
        if self._daily_flag:
            compare = 'CLOCKTIME'
        fire_time_hours=self._fire_time / 3600.0
        return 'Link %s %s AT %s %s'%(link_name, action, compare, fire_time_hours)

    # @classmethod
    # def WithTarget(self, fire_time, time_flag, daily_flag, target_obj, attribute, value):
    #     t = ControlAction(target_obj, attribute, value)
    #     return TimeControl(fire_time, time_flag, daily_flag, t)
    
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
            if wnm.prev_sim_time < self._fire_time and self._fire_time <= wnm.sim_time:
                return (True, int(wnm.sim_time - self._fire_time))
        elif self._time_flag == 'SHIFTED_TIME':
            if wnm.prev_shifted_time() < self._fire_time and self._fire_time <= wnm.shifted_time():
                return (True, int(round(wnm.shifted_time() - self._fire_time)))

        return (False, None)

    def _FireControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only fired if priority == self._priority.
        """
        if self._control_action is None:
            raise ValueError('_control_action is None inside TimeControl')

        if self._priority != priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
        if self._daily_flag:
            self._fire_time += 24*3600
        return change_flag, change_tuple, orig_value


class ConditionalControl(Control):
    """
    A class for creating controls that fire when a specified condition is satisfied. The control_action is
    fired/activated when the operation evaluated on the source object/attribute and the threshold is True.

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

    Examples
    --------
    >>> pipe = wn.get_link('pipe8')
    >>> tank = wn.get_node('tank3')
    >>> action = ControlAction(pipe, 'status', wntr.network.LinkStatus.closed)
    >>> control = ConditionalControl((tank, 'head'), numpy.greater_equal, 13.5, action)
    >>> wn.add_control('control_name', control)

    In this case, pipe8 will be closed if the head in tank3 becomes greater than or equal to 13.5 meters.

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
        

    def to_inp_string(self, flowunit):
        link_name = self._control_action._target_obj_ref.name()
        action = 'OPEN'
        if self._control_action._attribute == 'status':
            if self._control_action._value == 1:
                action = 'OPEN'
            else:
                action = 'CLOSED'
        else:
            action = str(self._control_action._value)
        target_name = self._source_obj.name()
        compare = 'ABOVE'
        if self._operation is np.less:
            compare = 'BELOW'
        threshold = convert('Hydraulic Head',flowunit,self._threshold-self._source_obj.elevation,False)
        return 'Link %s %s IF Node %s %s %s'%(link_name, action, target_name, compare, threshold)


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
        if type(self._source_obj)==wntr.network.Tank and self._source_attr=='head' and wnm.sim_time!=0 and self._partial_step_for_tanks:
            if presolve_flag:
                val = getattr(self._source_obj,self._source_attr)
                q_net = self._source_obj.prev_demand
                delta_h = 4.0*q_net*(wnm.sim_time-wnm.prev_sim_time)/(math.pi*self._source_obj.diameter**2)
                next_val = val+delta_h
                if self._operation(next_val, self._threshold) and self._operation(val, self._threshold):
                    return (False, None)
                if self._operation(next_val, self._threshold):
                    #if self._source_obj.name()=='TANK-3352':
                        #print 'threshold for tank 3352 control is ',self._threshold

                    m = (next_val-val)/(wnm.sim_time-wnm.prev_sim_time)
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
        elif type(self._source_obj==wntr.network.Tank) and self._source_attr=='head' and wnm.sim_time==0 and self._partial_step_for_tanks:
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

    def _FireControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only fired if priority == self._priority.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
        return change_flag, change_tuple, orig_value

class MultiConditionalControl(Control):
    """
    A class for creating controls that fire only when a set of specified conditions are all satisfied.

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

    Examples
    --------
    >>> pump = wn.get_link('pump1')
    >>> pipe = wn.get_link('pipe8')
    >>> tank = wn.get_node('tank3')
    >>> junction = wn.get_node('junction15')
    >>>
    >>> action = ControlAction(pump, 'status', wntr.network.LinkStatus.closed)
    >>>
    >>> sources = [(pipe,'flow'),(tank,'head')]
    >>> operations = [numpy.greater_equal, numpy.less_equal]
    >>> thresholds = [0.01, (junction,'head')]
    >>> control = MultiConditionalControl(sources, operations, thresholds, action)
    >>> wn.add_control('control_name', control)

    In this case, pump1 will be closed if the flowrate in pipe8 is greater than or equal to 0.01 cubic meters per
    second and the head in tank3 is less than or equal to the head in junction 15.

    """

    def __init__(self, source, operation, threshold, control_action):
        self.name = 'blah'
        self._priority = 0
        self._source = source
        self._operation = operation
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

    def __eq__(self, other):
        if self._control_action == other._control_action and \
           self.name            == other.name            and \
           self._priority       == other._priority       and \
           self._operation      == other._operation:
            for point1, point2 in zip(self._threshold, other._threshold):
                if type(point1) == tuple:
                    if not point1 == point2:
                        return False
                elif not abs(point1-point2)<1e-8:
                    return False
            return True
        else:
            return False

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
        for ndx in xrange(len(self._source)):
            src_obj = self._source[ndx][0]
            src_attr = self._source[ndx][1]
            src_val = getattr(src_obj, src_attr)
            oper = self._operation[ndx]
            if not isinstance(self._threshold[ndx],tuple):
                threshold_val = self._threshold[ndx]
            else:
                threshold_obj = self._threshold[ndx][0]
                threshold_attr = self._threshold[ndx][1]
                threshold_val = getattr(threshold_obj, threshold_attr)
            if not oper(src_val, threshold_val):
                action_required = False
                break

        if action_required:
            return (True, 0)
        else:
            return (False, None)

    def _FireControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that is being simulated/modified.
        priority : int
            A priority value. The action is only fired if priority == self._priority.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
        return change_flag, change_tuple, orig_value

class _CheckValveHeadControl(Control):
    """
    
    """
    def __init__(self, wnm, cv, operation, threshold, control_action):
        self.name = 'blah'
        self._priority = 3
        self._cv = cv
        self._operation = operation
        self._threshold = threshold
        self._control_action = control_action
        self._start_node_name = self._cv.start_node()
        self._end_node_name = self._cv.end_node()
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
        if self._operation(headloss, self._threshold):
            return (True, 0)
        return (False, None)
        
    def _FireControlActionImpl(self, wnm, priority):
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
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
        self._action_to_fire = None
        self._start_node_name = valve.start_node()
        self._end_node_name = valve.end_node()
        self._start_node = wnm.get_node(self._start_node_name)
        self._end_node = wnm.get_node(self._end_node_name)
        self._resistance_coefficient = 0.0826*0.02*self._valve.diameter**(-5)*self._valve.diameter*2.0

    @classmethod
    def WithTarget(self, source_obj, source_attribute, source_attribute_prev, operation, threshold, target_obj, target_attribute, target_value):
        ca = ControlAction(target_obj, target_attribute, target_value)
        return ConditionalControl(source_obj, source_attribute, source_attribute_prev, operation, threshold, ca)

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
                self._action_to_fire = self._close_control_action
                return (True, 0)
            Hl = self._resistance_coefficient*abs(self._valve.flow)**2
            if self._start_node.head < head_setting + Hl - self._Htol:
                self._action_to_fire = self._open_control_action
                return (True, 0)
            return (False, None)
        elif self._valve._status == wntr.network.LinkStatus.opened:
            if self._valve.flow < -self._Qtol:
                self._action_to_fire = self._close_control_action
                return (True, 0)
            Hl = self._resistance_coefficient*abs(self._valve.flow)**2
            if self._start_node.head > head_setting + Hl + self._Htol:
                self._action_to_fire = self._active_control_action
                return (True, 0)
            return (False, None)
        elif self._valve._status == wntr.network.LinkStatus.closed:
            if self._start_node.head > self._end_node.head + self._Htol and self._start_node.head < head_setting - self._Htol:
                self._action_to_fire = self._open_control_action
                return (True, 0)
            if self._start_node.head > self._end_node.head + self._Htol and self._end_node.head < head_setting - self._Htol:
                self._action_to_fire = self._active_control_action
                return (True, 0)
            return (False, None)

    def _FireControlActionImpl(self, wnm, priority):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._action_to_fire.FireControlAction(self.name)
        return change_flag, change_tuple, orig_value

