# -*- coding: utf-8 -*-
"""
Classes and methods used for specifying controls and control actions
that may modify parameters in the network during simulation.
"""

"""
Created on Sat Sep 26 12:33 AM 2015

@author: claird
"""

import wntr
import weakref
import numpy as np
import math

"""
Control Priorities:
0 is the lowest
3 is the highest

0:
   Open check valves/pumps if flow would be forward
   Open links for time controls
   Open links for conditional controls
   Open links connected to tanks if the tank head is larger than the minimum head plus a tolerance
   Open links connected to tanks if the tank head is smaller than the maximum head minus a tolerance
   Open pumps if power comes back up
   Start/stop leaks
1:
   Close links connected to tanks if the tank head is less than the minimum head (except check valves and pumps than only allow flow in).
   Close links connected to tanks if the tank head is larger than the maximum head (exept check valves and pumps that only allow flow out).
2:
   Open links connected to tanks if the level is low but flow would be in
   Open links connected to tanks if the level is high but flow would be out
   Close links connected to tanks if the level is low and flow would be out
   Close links connected to tanks if the level is high and flow would be in
3:
   Close links for time controls
   Close links for conditional controls
   Close check valves/pumps for negative flow
   Close pumps without power
"""

class BaseControlAction(object):
    """ 
    A base class for deriving new control actions.
    The control action is fired by calling FireAction

    This class is not meant to be used directly. Derived classes
    must implement the FireActionImpl method.
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
        Implements the specific action that will be fired when FireAction
        is called. This method should be overridded in derived classes
        """
        raise NotImplementedError('_FireActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')

class ControlAction(BaseControlAction):
    """
    A general class for specifying an ControlAction that simply
    modifies the attribute of a target.

    Parameters
    ----------
    target_obj : object
        object that will be changed when the event is fired

    attribute : string
        the attribute that will be changed on the object when
        the event is fired

    value : any
        the new value for the attribute when the event is fired
    """
    def __init__(self, target_obj, attribute, value):
        if target_obj is None:
            raise ValueError('target_obj is None in ControlAction::__init__. A valid target_obj is needed.')
        if not hasattr(target_obj, attribute):
            raise ValueError('attribute given in ControlAction::__init__ is not valid for target_obj')

        self._target_obj_ref = weakref.ref(target_obj)
        self._attribute = attribute
        self._value = value

        #if (isinstance(target_obj, wntr.network.Valve) or (isinstance(target_obj, wntr.network.Pipe) and target_obj.cv)) and attribute=='status':
        #    raise ValueError('You may not add controls to valves or pipes with check valves.')

    def _FireControlActionImpl(self, control_name):
        """
        This is an overridden method from the ControlAction class. 
        Here, it changes the target_obj's attribute to the provided value.

        This method should not be called directly. Use FireAction of the 
        ControlAction base class instead.
        """
        target = self._target_obj_ref()
        if target is None:
            raise ValueError('target is None inside TargetAttribureControlAction::_FireControlActionImpl. This may be because a target_obj was added, but later the object itself was deleted.')
        if not hasattr(target, self._attribute):
            raise ValueError('attribute specified in ControlAction is not valid for targe_obj')
        
        orig_value = getattr(target, self._attribute)
        if orig_value == self._value:
            return False, None, None
        else:
            #print control_name
            #print 'setting ',target.name(),self._attribute,' to ',self._value
            setattr(target, self._attribute, self._value)
            return True, (target, self._attribute), orig_value

class Control(object):
    """
    This is the base class for all control objects.
    Control objects are used to modify a model based on current
    state in the simulation. For example, if a pump is supposed 
    to be turned on when the simulation time reaches 6 AM, or a
    pipe is supposed to be closed when a tank reaches a minimum
    height.

    From an implementation standpoint, derived Control classes
    implement a particular mechanism for monitoring state (e.g.
    checking the simulation time to see if a change should be
    made). Then, they typically call FireAction on a derived
    ControlAction class.

    New control classes (classes derived from Control) must implement
    the following methods:
       _IsControlActionRequired(self, wnm)
       _FireControlAction(self, wnm)
    """
    def __init__(self):
        pass

    def IsControlActionRequired(self, wnm, presolve_flag):
        """
        This method is called to see if any action is required
        by this control object. This method returns a tuple
        that indicates if action is required and a recommended
        time for the simulation to backup (in seconds as a positive
        number) before firing the control action.

        Note: The control action will actually be fired when 
        _IsActionRequiredImpl returns (True, t) with a t that is 
        lower than a simulator tolerance - indicating that
        action is required and no additional time backup is required.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that
            is being simulated.

        presolve_flag : bool
            This is true if we are calling before the solve, and false if 
            we are calling after the solve.
        """
        return self._IsControlActionRequiredImpl(wnm, presolve_flag)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This method should be implemented in derived Control classes as 
        the main implementation of IsControlActionRequired.

        The derived classes that override this method should return 
        a tuple that indicates if action is required and a recommended
        time for the simulation to backup before firing the control 
        action.

        This method should not be called directly. Use IsControlActionRequired
        instead. For more details see documentation for IsControlActionRequired
        """
        raise NotImplementedError('_IsControlActionRequiredImpl is not implemented. '
                                  'This method must be implemented in any '
                                  ' class derived from Control.')  

    def FireControlAction(self, wnm, priority):
        """
        This method is called to fire the control action after
        a call to IsControlActionRequired indicates that an action is required.

        Note: Derived classes should not override this method, but should
        override _FireControlActionImpl instead.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that
            is being simulated.
        """
        return self._FireControlActionImpl(wnm, priority)

    def _FireControlActionImpl(self, wnm):
        """
        This is the method that should be overridden in derived classes
        to implement the action of firing the control.

        Parameters
        ----------
        wnm : WaterNetworkModel
            An instance of the current WaterNetworkModel object that
            is being simulated.
        """
        raise NotImplementedError('_FireControlActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')


class TimeControl(Control):
    """
    A class for creating time controls to fire a control action at a
    particular time.

    Parameters
    ----------
    wnm : WaterNetworkModel object

    fire_time : float
        time (in seconds) when the events should be fired.

    time_flag : string, ('SIM_TIME', 'SHIFTED_TIME')

        SIM_TIME: indicates that the value of fire_time is in seconds
            since the start of the simulation

        SHIFTED_TIME: indicates that the value of fire_time is shifted
            by the start time set for the simulation. That is,
            fire_time is in seconds since 12 AM on the first day of the
            simulation.  Therefore, 7200 refers to 2:00 AM regardless
            of the start time in the simulation.

    daily_flag : bool
        False : control will execute once when time is first encountered
        True : control will execute at the same time daily

    control_action : An object derived from ControlAction This is the
       event action that will be fired at the specified time
    """

    def __init__(self, wnm, fire_time, time_flag, daily_flag, control_action):
        self.name = 'blah'

        if isinstance(control_action._target_obj_ref(),wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.opened:
            self._priority = 0
        elif isinstance(control_action._target_obj_ref(),wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.closed:
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

    @classmethod
    def WithTarget(self, fire_time, time_flag, daily_flag, target_obj, attribute, value):
        t = ControlAction(target_obj, attribute, value)
        return TimeControl(fire_time, time_flag, daily_flag, t)
    
    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
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
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
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

    def __init__(self, source, operation, threshold, control_action):
        self.name = 'blah'

        if isinstance(control_action._target_obj_ref(),wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.opened:
            self._priority = 0
        elif isinstance(control_action._target_obj_ref(),wntr.network.Link) and control_action._attribute=='status' and control_action._value==wntr.network.LinkStatus.closed:
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

    @classmethod
    def WithTarget(self, source, operation, threshold, target_obj, target_attribute, target_value):
        ca = ControlAction(target_obj, target_attribute, target_value)
        return ConditionalControl(source, operation, threshold, ca)

    def _IsControlActionRequiredImpl(self, wnm, presolve_flag):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if type(self._source_obj)==wntr.network.Tank and self._source_attr=='head' and wnm.sim_time!=0 and self._partial_step_for_tanks:
            if presolve_flag:
                val = getattr(self._source_obj,self._source_attr)
                q_net = self._source_obj.prev_demand
                delta_h = 4.0*q_net*(wnm.sim_time-wnm.prev_sim_time)/(math.pi*self._source_obj.diameter**2)
                next_val = val+delta_h
                if self._operation(next_val, self._threshold) and self._operation(val, self._threshold):
                    return (True, None)
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
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
        return change_flag, change_tuple, orig_value

class MultiConditionalControl(Control):

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

        action_required = True
        for ndx in xrange(len(self._source)):
            src_obj = self._source[ndx][0]
            src_attr = self._source[ndx][1]
            src_val = getattr(src_obj, src_attr)
            oper = self._operation[ndx]
            if isinstance(self._threshold[ndx],float):
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
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._priority!=priority:
            return False, None, None

        change_flag, change_tuple, orig_value = self._control_action.FireControlAction(self.name)
        return change_flag, change_tuple, orig_value

class _CheckValveHeadControl(Control):
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
            Hml = self._valve.minor_loss*self._valve.flow**2
            if self._start_node.head < head_setting + Hml - self._Htol:
                self._action_to_fire = self._open_control_action
                return (True, 0)
            return (False, None)
        elif self._valve._status == wntr.network.LinkStatus.opened:
            if self._valve.flow < -self._Qtol:
                self._action_to_fire = self._close_control_action
                return (True, 0)
            Hml = self._valve.minor_loss*self._valve.flow**2
            if self._start_node.head > head_setting + Hml + self._Htol:
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

