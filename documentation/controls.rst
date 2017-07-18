.. raw:: latex

    \clearpage

Water network controls
======================================

One of the key features of water network models is the ability to control pipes, pumps and valves using simple and complex conditions.  
EPANET uses "controls" and "rules" to define conditions [Ross00]_.
A control is a single action (i.e., closing/opening a link or changing the setting) based on a single condition (i.e., time based or tank level based).
A rule is more complex; rules take an IF-THEN-ELSE form and can have multiple conditions and multiple actions in each of the logical blocks.
WNTR supports EPANET's rules and controls when generating a water network model from and INP file and simulating hydraulics using the EpanetSimulator.
WNTR includes additional options to define controls that can be used by the WNTRSimulator.

The basic steps to define a control for a water network model are:

1. Define the control action
2. Define the control or rule using the control action
3. Add the control or rule to the network

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


Simple controls
---------------------

Control objects that emulate EPANET's [CONTROLS] section are defined in two classes: :class:`~wntr.network.controls.ConditionalControl` and :class:`~wntr.netowrk.controls.TimeControl`.
When generating a water network model from an EPANET INP file, a ConditionalControl or TimeControl will be created for each control.

**Conditional controls**: 
ConditionalControl objects define tank level and junction pressure based controls.
Conditional controls require a source, operation, threshold, and a control action.
The source is defined as tuple where the first value is a water network model component and the second value is the attribute of the object.
The operation is defined using NumPy functions such as  `np.greater` and `np.less`.
The threshold is the value that triggers the condition to the true.
The control action is defined above.

In the following example, a conditional control is defined that opens pipe 330 if the level of tank 1 goes above 46.0248 m.
The source is the the tank level and is defined as a tuple with the node object `n1` and the attribute `level`.
To specify that the condition should be true when the level is greater than the threshold, the operation is set to `np.greater` and the threshold is set to 46.0248.
The control action `act1` from above is used in the conditional control:

.. doctest::
	
    >>> n1 = wn.get_node('1')
    >>> thresh1 = 46.0248
    >>> ctrl1 = controls.ConditionalControl( (n1, 'level'), np.greater, thresh1, act1)
    >>> ctrl1
    <ConditionalControl: <Tank '1'>, 'level'), <ufunc 'greater'>, 46.0248, <ControlAction: <Pipe '330'>, 'status', 'Open'>>

To get an EPANET-like description of this control, use the print function:

.. doctest::

    >>> print(ctrl1)
    LINK 330 Open IF NODE 1 Above 46.0248

**Time-based controls**: 
TimeControl objects define time-based controls.
Time-based controls require a water network model object, a time to start the condition, a control action, and additional flags to specify the time reference point and recurrence.
The time flag is either `SIM_TIME` or `SHIFTED_TIME`; these indicate simulation or clock time, respectively.
The daily flag is either True or False and indicates if the control should be repeated every 24 hours.

In the following example, a time-based control is defined that opens Pump 10 at hour 121.
The time flag is set to `SIM_TIME` and the daily flag is set to False.
A new control action is defined that opens the pump:

.. doctest::

    >>> time2 = 121 * 60 * 60 
    >>> timeflag2 = 'SIM_TIME'
    >>> dailyflag2 = False
    >>> pump2 = wn.get_link('10')
    >>> act2 = controls.ControlAction(pump2, 'status', 1)
    >>> ctrl2 = controls.TimeControl(wn, time2, timeflag2, dailyflag2, act2)
    >>> print(ctrl2)
    LINK 10 Open AT TIME 121:00:00

Note that the EpanetSimulator is limited to use the following pairs: 
time_flag='SIM_TIME' with daily_flag=False, and 
time_flag='SHIFTED_TIME' with daily_flag=True.
The WNTRSimulator can use any combination of time flag and daily flag.

Complex rules
--------------------------

Control objects that emulate EPANET's [RULES] section are defined in the :class:`~wntr.network.controls.IfThenElseControl` class.
When generating a water network model from an EPANET INP file, an IfThenElseControl will be created for each rule.
An IfThenElseControl is defined using a :class:`~wntr.network.controls.ControlCondition` object and a :class:`~wntr.network.controls.ControlAction` object.
Condition classes are listed in :numref:`table-condition-classes`.  

.. _table-condition-classes:
.. table:: Condition Classes

   ===================================================  ========================================================================================
   Condition class                                      Description
   ===================================================  ========================================================================================
   :class:`~wntr.network.controls.TimeOfDayCondition`	Time-of-day or “clocktime” based condition statement.
   :class:`~wntr.network.controls.SimTimeCondition`	    Condition based on time since start of the simulation.
   :class:`~wntr.network.controls.ValueCondition`	    Compare a network element attribute to a set value
   :class:`~wntr.network.controls.RelativeCondition`	Compare attributes of two different objects (e.g., levels from tanks 1 and 2)
   :class:`~wntr.network.controls.OrCondition`	        Combine two WNTR Conditions with an OR.
   :class:`~wntr.network.controls.AndCondition`	        Combine two WNTR Conditions with an AND
   ===================================================  ========================================================================================
   
All the above conditions are valid EPANET conditions except RelativeCondition; however, some advanced features of may not be defined.

In the following example, the previous simple controls are recreated using the IfThenElseControl:

.. doctest::

    >>> cond1 = controls.ValueCondition(n1, 'level', '>', 46.0248)
    >>> print(cond1)
    Tank('1').level > 46.0248
    
    >>> rule1 = controls.IfThenElseControl(cond1, [act1], name='control1')
    >>> print(rule1)
    Rule control1 := if Tank('1').level > 46.0248 then set Pipe('330').status to Open
    
    >>> cond2 = controls.SimTimeCondition(wn, '=', '121:00:00')
    >>> print(cond2)
    sim_time = 435600 sec
    
    >>> rule2 = controls.IfThenElseControl(cond2, [act2], name='control2')
    >>> print(rule2)
    Rule control2 := if sim_time = 435600 sec then set Pump('10').status to Open


More complex rules can be written using one of the Boolean logic condition classes.
The following example creates a new rule that will open pipe 330 if both conditions are true, and otherwise it will open pipe 10; this rule will behave very differently from the rules above:

.. doctest::

    >>> cond3 = controls.AndCondition(cond1, cond2)
    >>> print(cond3)
    ( Tank('1').level > 46.0248 && sim_time = 435600 sec )
    
    >>> rule3 = controls.IfThenElseControl(cond3, [ act1 ], [ act2 ], priority=3, name='weird')
    >>> print(rule3)
    Rule weird := if ( Tank('1').level > 46.0248 && sim_time = 435600 sec ) then set Pipe('330').status to Open else set Pump('10').status to Open with priority 3

Actions can also be combined, as shown in the following example:

.. doctest::

    >>> cond4 = controls.OrCondition(cond1, cond2)
    >>> rule4 = controls.IfThenElseControl(cond4, [act1, act2])
    >>> print(rule4)
    Rule  := if ( Tank('1').level > 46.0248 || sim_time = 435600 sec ) then set Pipe('330').status to Open and set Pump('10').status to Open

The flexibility of the IfThenElseControl combined with the different ControlCondition classes and ControlActions provides an extremely powerful tool for defining complex network operations.

Adding controls to a network
-------------------------------

Once a control is created, they must be added to the network.
This is accomplished using the :class:`~wntr.network.model.WaterNetworkModel.add_control` method of the water network model object.
The control should be named so that it can be retrieved and modified if desired:

.. doctest::

    >>> wn.add_control('NewTimeControl', ctrl2)
    >>> wn.get_control('NewTimeControl')
    <TimeControl: model, 435600, 'SIM_TIME', False, <ControlAction: <Pump '10'>, 'status', 'Open'>>

..
	If a control of that name already exists, an error will occur. In this case, the control will need to be deleted first.

	.. doctest::

		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
		ValueError: The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.
		>>> wn.remove_control('NewTimeControl')
		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
