# -*- coding: utf-8 -*-
"""
Classes and methods used for specifying controls and control actions
that may modify parameters in the network during simulation.
"""

"""
Created on Sat Sep 26 12:33 AM 2015

@author: claird
"""

import weakref
import numpy as np

class ControlAction(object):
    """ 
    A base class for deriving new control actions.
    The control action is fired by calling FireAction

    This class is not meant to be used directly. Derived classes
    must implement the FireActionImpl method.
    """
    def __init__(self):
        pass

    def FireControlAction(self):
        """ 
        This method is called to fire the corresponding control action.
        """
        self._FireControlActionImpl()

    def _FireControlActionImpl(self):
        """
        Implements the specific action that will be fired when FireAction
        is called. This method should be overridded in derived classes
        """
        raise NotImplementedError('_FireActionImpl is not implemented. '
                                  'This method must be implemented in '
                                  'derived classes of ControlAction.')

class TargetAttributeControlAction(ControlAction):
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
            raise ValueError('target_obj is None in TargetAttributeControlAction::__init__. A valid target_obj is needed.')
        if not hasattr(target_obj, attribute):
            raise ValueError('attribute given in TargetAttributeControlAction::__init__ is not valid for target_obj')

        self._target_obj_ref = weakref.ref(target_obj)
        self._attribute = attribute
        self._value = value

    def _FireControlActionImpl(self):
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
            raise ValueError('attribute specified in TargetAttributeControlAction is not valid for targe_obj')
        
        setattr(target, self._attribute, self._value)

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

    def IsControlActionRequired(self, wnm):
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
        return self._IsControlActionRequiredImpl(wnm)

    def _IsControlActionRequiredImpl(self, wnm):
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

    def FireControlAction(self, wnm):
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
        self._FireControlActionImpl(wnm)

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
        t = TargetAttributeControlAction(target_obj, attribute, value)
        return TimeControl(fire_time, time_flag, daily_flag, t)
    
    def _IsControlActionRequiredImpl(self, wnm):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._time_flag == 'SIM_TIME':
            if wnm.prev_sim_time < self._fire_time and self._fire_time <= wnm.sim_time:
                return (True, int(wnm.sim_time - self._fire_time))
        elif self._time_flag == 'SHIFTED_TIME':
            if wnm.prev_shifted_time() < self._fire_time and self._fire_time <= wnm.shifted_time():
                return (True, int(wnm.shifted_time() - self._fire_time))

        return (False, None)

    def _FireControlActionImpl(self, wnm):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        if self._control_action is None:
            raise ValueError('_control_action is None inside TimeControl')

        self._control_action.FireControlAction()
        if self._daily_flag:
            self._fire_time += 24*3600

class ConditionalControl(Control):
    """
    A class for creating conditional controls to fire a control action
    when a particular object/attribute becomes higher or lower than a 
    specified value.

    Parameters
    ----------
    source_obj : object
       The source object that contains the attribute being monitored

    source_attribute : string
       The name of the attribute being monitored

    operation : one the numpy operations listed below
       The comparison operation to be used. This must be 
       one of the numpy comparison operations, e.g.:

       greater(x1, x2[, out]) Return the truth value of (x1 > x2) element-wise.
       greater_equal(x1, x2[, out]) Return the truth value of (x1 >= x2) element-wise.
       less(x1, x2[, out]) Return the truth value of (x1 < x2) element-wise.
       less_equal(x1, x2[, out]) Return the truth value of (x1 =< x2) element-wise.

    threshold : float or tuple 
       The threshold value to compare against. If a float is passed,
       this threshold is considered constant. If a tuple is passed, it
       is taken as (object2, attribute2), and the source_attribute on
       the source_obj will be compared to attribute2 on object2.

    control_action : An object derived from ControlAction 
       This is the event action that will be fired when the condition becomes true
    """

    def __init__(self, source_obj, source_attribute, operation, threshold, control_action):
        self._source_obj = source_obj
        self._source_attribute = source_attribute
        self._prev_source_attr_value = None
        self._prev_threshold_attr_value = None
        self._operation = operation
        self._control_action = control_action
        self._constant_threshold = None
        self._threshold = None
        self._threshold_obj = None
        self._threshold_attr = None

        if type(threshold) == float:
            self._constant_threshold = True
            self._threshold = threshold
        else:
            self._constant_threshold = False
            self._threshold_obj = threshold[0]
            self._threshold_attr = threshold[1]

        if source_obj is None:
            raise ValueError('source_obj of None passed to ConditionalControlObject.')
        if not hasattr(source_obj, source_attribute):
            raise ValueError('In ConditionalControlObject, source_obj does not contain the attribute specified by source_attribute.')
        if not hasattr(self.threshold_obj, self._threshold_attr):
            raise ValueError('In ConditionalControlObject, the threshold object does not contain the specified attribute.')

    @classmethod
    def WithTarget(self, source_obj, source_attribute, source_attribute_prev, operation, threshold, target_obj, target_attribute, target_value):
        ca = TargetAttributeControlAction(target_obj, target_attribute, target_value)
        return ConditionalControl(source_obj, source_attribute, source_attribute_prev, operation, threshold, ca)

    def _IsControlActionRequiredImpl(self, wnm):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        value = getattr(source_obj, source_attribute)
        prev_value = getattr(source_obj, source_attribute_prev)
        if self._operation(value, self._threshold):
            # control action is required
            if wnm.prev_sim_time is None or prev_value is None:
                assert wnm.time_step == 0, 'This should only happen during the first simulation timestep'
                return (True, 0)
                
            # let's do linear interpolation to determine the estimated switch time
            m = (value - prev_value)/(wnm.sim_time - wnm.prev_sim_time)
            new_time = (self._threshold - prev_value)/m + wnm.prev_sim_time
            return (True, new_time)
        
        return (False, None)
        

    def _FireControlActionImpl(wnm):
        """
        This implements the derived method from Control. Please see
        the Control class and the documentation for this class.
        """
        assert self._control_action is not None, '_control_action is None inside TimeControl'
        self._control_action.FireControlAction(wnm)



    
