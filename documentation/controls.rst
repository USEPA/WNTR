.. raw:: latex

    \clearpage

Water network controls
======================================

One of the key features of water network models is the ability to control pipes, pumps, and valves using simple and complex conditions.  
EPANET uses "controls" and "rules" to define conditions [Ross00]_.
A control is a single action (i.e., closing/opening a link or changing the setting) based on a single condition (i.e., time based or tank level based).
A rule is more complex; rules take an IF-THEN-ELSE form and can have multiple conditions and multiple actions in each of the logical blocks.
WNTR supports EPANET's rules and controls when generating a water network model from an EPANET INP file and simulating hydraulics using either the EpanetSimulator or the WNTRSimulator.
WNTR includes additional options to define controls that can be used by the WNTRSimulator.

The basic steps to define a control for a water network model are:

1. Define the control action(s)
2. Define condition(s) (i.e., define what should cause the action to occur)
3. Define the control or rule using the control action(s) and condition(s)
4. Add the control or rule to the network

These steps are defined below.  Examples use the "Net3.inp" EPANET INP file to generate the water network model object, called `wn`.

Control actions
-----------------------

Control actions tell the simulator what to do when a condition becomes "true." 
Control actions are created using the :class:`~wntr.network.controls.ControlAction` class.
A control action is defined by a target link, the property to change, and the value to change it to.
The following example creates a control action that opens pipe 330:

.. doctest::
    :hide:

    >>> import wntr
    >>> import numpy as np
    >>> from __future__ import print_function
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
    ...
    >>> print(wn)   # doctest: +SKIP
    <WaterNetworkModel object at 0x03978184 >


.. doctest::

    >>> import wntr.network.controls as controls
    >>> l1 = wn.get_link('330')
    >>> act1 = controls.ControlAction(l1, 'status', 1)
    >>> print(act1)
    set Pipe('330').status to Open


Conditions
----------

Conditions define when a control action should occur. The condition classes are listed in :numref:`table-condition-classes`.

.. _table-condition-classes:
.. table:: Condition Classes

   ====================================================  ========================================================================================
   Condition class                                       Description
   ====================================================  ========================================================================================
   :class:`~wntr.network.controls.TimeOfDayCondition`	 Time-of-day or “clocktime” based condition statement
   :class:`~wntr.network.controls.SimTimeCondition`	     Condition based on time since start of the simulation
   :class:`~wntr.network.controls.ValueCondition`	     Compare a network element attribute to a set value
   :class:`~wntr.network.controls.TankLevelCondition`    Compare the level in a tank to a set value.
   :class:`~wntr.network.controls.RelativeCondition`	 Compare attributes of two different objects (e.g., levels from tanks 1 and 2)
   :class:`~wntr.network.controls.OrCondition`	         Combine two WNTR Conditions with an OR
   :class:`~wntr.network.controls.AndCondition`	         Combine two WNTR Conditions with an AND
   ====================================================  ========================================================================================

All of the above conditions are valid EPANET conditions except RelativeCondition.


General Controls and Rules
--------------------------
All controls and rules may be created in WNTR with the :class:`~wntr.network.controls.Control` class, which takes an instance 
of any of the above conditions, an iterable of :class:`~wntr.network.controls.ControlAction` instances that should occur when 
the condition is true, and an optional iterable of :class:`~wntr.network.controls.ControlAction` instances that should occur 
when the condition is false. The :class:`~wntr.network.controls.Control` class also takes optional priority and name arguments. 
If multiple controls with conflicting actions should occur at the same time, the control with the highest priority will override 
all others. The priority argument should be an element of the :class:`~wntr.network.controls.ControlPriority` enum. The default 
priority is medium (3). The name argument should be a string.

The following examples illustrate the creation of controls/rules in WNTR:

.. doctest::

    >>> n1 = wn.get_node('1')
    >>> cond1 = controls.ValueCondition(n1, 'level', '>', 46.0248)
    >>> print(cond1)
    Tank('1').level > 46.0248
    
    >>> rule1 = controls.Control(cond1, [act1], name='control1')
    >>> print(rule1)
    rule control1 := if Tank('1').level > 46.0248 then set Pipe('330').status to Open with priority 3
    
    >>> cond2 = controls.SimTimeCondition(wn, '=', '121:00:00')
    >>> print(cond2)
    sim_time = 435600 sec
    
    >>> pump2 = wn.get_link('10')
    >>> act2 = controls.ControlAction(pump2, 'status', 1)
    >>> rule2 = controls.Control(cond2, [act2], name='control2')
    >>> print(rule2)
    rule control2 := if sim_time = 435600 sec then set HeadPump('10').status to Open with priority 3


More complex controls/rules can be written using one of the Boolean logic condition classes.
The following example creates a new rule that will open pipe 330 if both conditions are true, and otherwise it will open pipe 10. This rule will behave very differently from the rules above:

.. doctest::

    >>> cond3 = controls.AndCondition(cond1, cond2)
    >>> print(cond3)
    ( Tank('1').level > 46.0248 && sim_time = 435600 sec )
    
    >>> rule3 = controls.Control(cond3, [ act1 ], [ act2 ], priority=3, name='complex_control')
    >>> print(rule3)
    rule complex_control := if ( Tank('1').level > 46.0248 && sim_time = 435600 sec ) then set Pipe('330').status to Open else set HeadPump('10').status to Open with priority 3

Actions can also be combined, as shown in the following example:

.. doctest::

    >>> cond4 = controls.OrCondition(cond1, cond2)
    >>> rule4 = controls.Control(cond4, [act1, act2])
    >>> print(rule4)
    rule  := if ( Tank('1').level > 46.0248 || sim_time = 435600 sec ) then set Pipe('330').status to Open and set HeadPump('10').status to Open with priority 3

The flexibility of the :class:`~wntr.network.controls.Control` class combined with the different :class:`~wntr.network.controls.ControlCondition` classes and :class:`~wntr.network.controls.ControlAction` instances provides an extremely powerful tool for defining complex network operations.

    
Simple controls
---------------------

Simple controls (contols that emulate EPANET's [CONTROLS] section) may be defined more simply and concisely using the class methods of :class:`~wntr.network.controls.Control`: :class:`~wntr.network.controls.Control.time_control` and :class:`~wntr.network.controls.Control.conditional_control`. 

**Conditional controls**: 
Control objects created with the :class:`~wntr.network.controls.Control.conditional_control` class method define tank level and junction pressure based controls.
Conditional controls require a source, attribute, operation, threshold, and a control action.
The source is a water network model component and the attribute is any valid attribute for that object.
The operation is defined using NumPy functions such as  `np.greater` and `np.less` or elements of the :class:`~wntr.network.controls.Comparison` enum.
The threshold is the value that triggers the condition to be true.
The control action is defined above.

In the following example, a conditional control is defined that opens pipe 330 if the level of tank 1 goes above 46.0248 m.
The source is the tank `n1` and the attribute is the `level`.
To specify that the condition should be true when the level is greater than the threshold, the operation is set to `np.greater` and the threshold is set to 46.0248.
The control action `act1` from above is used in the conditional control:

.. doctest::
	
    >>> n1 = wn.get_node('1')
    >>> thresh1 = 46.0248
    >>> ctrl1 = controls.Control.conditional_control(n1, 'level', np.greater, thresh1, act1)
    >>> print(ctrl1)
    pre_and_postsolve  := if Tank('1').level > 46.0248 then set Pipe('330').status to Open with priority 3
    
**Time-based controls**: 
Control objects created with the :class:`~wntr.network.controls.Control.time_control` class method define time-based controls.
Time-based controls require a water network model object, a time at which the action should occur, a control action, and additional flags to specify the time reference point and recurrence.
The time flag is either `SIM_TIME` or `SHIFTED_TIME`; these indicate simulation or clock time, respectively.
The daily flag is either True or False and indicates if the control should be repeated every 24 hours.

In the following example, a time-based control is defined that opens Pump 10 at hour 121.
The time flag is set to `SIM_TIME` and the daily flag is set to False.
A new control action is defined that opens the pump:

.. doctest::

    >>> time2 = 121 * 60 * 60 
    >>> timeflag2 = 'SIM_TIME'
    >>> dailyflag2 = False
    >>> ctrl2 = controls.Control.time_control(wn, time2, timeflag2, dailyflag2, act2)
    >>> print(ctrl2)
    presolve  := if sim_time = 435600.0 sec then set HeadPump('10').status to Open with priority 3

Note that the EpanetSimulator is limited to use the following pairs: 
time_flag='SIM_TIME' with daily_flag=False, and 
time_flag='SHIFTED_TIME' with daily_flag=True.
The WNTRSimulator can use any combination of time flag and daily flag.
   

Adding controls to a network
-------------------------------

Once a control is created, they can be added to the network.
This is accomplished using the :class:`~wntr.network.model.WaterNetworkModel.add_control` method of the water network model object.
The control should be named so that it can be retrieved and modified if desired:

.. doctest::

    >>> wn.add_control('NewTimeControl', ctrl2)
    >>> wn.get_control('NewTimeControl')
    <Control: '', <SimTimeCondition: model, 'Is', '5-01:00:00', False, 0>, [<ControlAction: 10, status, Open>], [], priority=3>

..
	If a control of that name already exists, an error will occur. In this case, the control will need to be deleted first.

	.. doctest::

		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
		ValueError: The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.
		>>> wn.remove_control('NewTimeControl')
		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
