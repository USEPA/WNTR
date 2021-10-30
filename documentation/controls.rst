.. raw:: latex

    \clearpage
	
Water network controls
======================================

One of the key features of water network models is the ability to control pipes, pumps, and valves using simple and complex conditions.  
EPANET uses "controls" and "rules" to define conditions [Ross00]_. WNTR replicates EPANET functionality, and includes additional options, as described below. The EPANET user manual provides more information on simple controls and rule-based controls (controls and rules, respectively in WNTR) [Ross00]_.

**Controls** are defined using an "IF condition; THEN action" format.  
Controls use a single action (i.e., closing/opening a link or changing the setting) based on a single condition (i.e., time based or tank level based).
If a time based or tank level condition is not exactly matched at a simulation timestep, controls make use of partial timesteps to match the condition before the control is deployed.
Controls in WNTR emulate EPANET simple controls.

**Rules** are more complex; rules are defined using an "IF condition; THEN action1; ELSE action2" format, where the ELSE block is optional.
Rules can use multiple conditions and multiple actions in each of the logical blocks.  Rules can also be prioritized to set the order of operation.
If rules with conflicting actions should occur at the same time, the rule with the highest priority will override all others.
Rules operate on a rule timestep specified by the user, which can be different from the simulation timestep.  
Rules in WNTR emulate EPANET rule-based controls.

When generating a water network model from an EPANET INP file, WNTR generates controls and rules based on input from the [CONTROLS] and [RULES] sections.  
These controls and rules are then used when simulating hydraulics with either the EpanetSimulator or the WNTRSimulator.
Controls and rules can also be defined directly in WNTR using the API described below.
WNTR includes additional options to define controls and rules that can be used by the WNTRSimulator.

The basic steps to define a control or rule are:

1. Define the action(s) (i.e., define the action that should occur, such as closing/opening a link)
2. Define condition(s) (i.e., define what should cause the action to occur, such as a tank level)
3. Define the control or rule using the action(s) and condition(s) (i.e., combine the defined action and condition)
4. Add the control or rule to the water network model

These steps are defined below.  

.. only:: latex

   See the `online API documentation <https://wntr.readthedocs.io/en/latest/apidoc/wntr.network.controls.html>`_ for more information on controls.
   
Actions
-----------------------

Control and rule actions tell the simulator what to do when a condition becomes "true." 
Actions are created using the :class:`~wntr.network.controls.ControlAction` class.
An action is defined by a target link, the attribute to change, and the value to change it to.
The following example creates an action that opens pipe 330, in which a status of 1 means open:

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
    ...

.. doctest::

    >>> import wntr # doctest: +SKIP
    >>> import wntr.network.controls as controls
	
    >>> wn = wntr.network.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP
    >>> pipe = wn.get_link('330')
    >>> act1 = controls.ControlAction(pipe, 'status', 1)
    >>> print(act1)
    PIPE 330 STATUS IS OPEN

Conditions
----------

Conditions define when an action should occur. The condition classes are listed in :numref:`table-condition-classes`.

.. _table-condition-classes:
.. table:: Condition Classes

   ====================================================  ========================================================================================
   Condition class                                       Description
   ====================================================  ========================================================================================
   :class:`~wntr.network.controls.TimeOfDayCondition`	 Time-of-day or “clocktime” based condition statement
   :class:`~wntr.network.controls.SimTimeCondition`	     Condition based on time since start of the simulation
   :class:`~wntr.network.controls.ValueCondition`	     Compare a network element attribute to a set value
   :class:`~wntr.network.controls.RelativeCondition`	 Compare attributes of two different objects (e.g., levels from tanks 1 and 2)
   :class:`~wntr.network.controls.OrCondition`	         Combine two WNTR conditions with an OR
   :class:`~wntr.network.controls.AndCondition`	         Combine two WNTR conditions with an AND
   ====================================================  ========================================================================================

All of the above conditions are valid EpanetSimulator conditions except :class:`~wntr.network.controls.RelativeCondition`.
The EpanetSimulator is also limited to always
repeat conditions that are defined with :class:`~wntr.network.controls.TimeOfDayCondition` and 
not repeat conditions that are defined with in :class:`~wntr.network.controls.SimTimeCondition`.
The WNTRSimulator can handle repeat or not repeat options for both of these conditions.

Controls
---------------------

A control is created in WNTR with the :class:`~wntr.network.controls.Control` class, which takes an instance 
of any of the above conditions, and an action that should occur when the condition is true. 

Controls are also assigned a priority. 
If controls with conflicting actions should occur at the same time, the control with the highest priority will override 
all others. The priority argument should be an element of the :class:`~wntr.network.controls.ControlPriority` class. The default 
priority is medium (3). 

In the following example, a conditional control is defined that opens pipe 330 if the level of tank 1 goes above 46.0248 m (151.0 ft).
The target is the tank and the attribute is the tank's level.
To specify that the condition should be true when the level is greater than the threshold, the operation is set to > and the threshold is set to 46.0248.
The action `act1` from above is used in the control.

.. doctest::
	
    >>> tank = wn.get_node('1')
    >>> cond1 = controls.ValueCondition(tank, 'level', '>', 46.0248)
    >>> print(cond1)
    TANK 1 LEVEL ABOVE 46.0248
    
    >>> ctrl1 = controls.Control(cond1, act1, name='control1')
    >>> print(ctrl1)
    IF TANK 1 LEVEL ABOVE 46.0248 THEN PIPE 330 STATUS IS OPEN PRIORITY 3
    
In the following example, a time-based control is defined that opens pump 10 at hour 121.
A new action is defined that opens the pump. The SimTimeCondition parameter can be specified as decimal hours
or as a string in ``[dd-]hh:mm[:ss]`` format. When printed, the output is converted to seconds.

.. doctest::
    
    >>> pump = wn.get_link('10')
    >>> act2 = controls.ControlAction(pump, 'status', 1)
    >>> cond2 = controls.SimTimeCondition(wn, '=', '121:00:00')
    >>> print(cond2)
    SYSTEM TIME IS 121:00:00
    
    >>> ctrl2 = controls.Control(cond2, act2, name='control2')
    >>> print(ctrl2)
    IF SYSTEM TIME IS 121:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 3

Rules
--------------------------
A rule is created in WNTR with the :class:`~wntr.network.controls.Rule` class, which takes any of the above conditions, 
a list of actions that should occur when the condition is true, and an optional list of actions that should occur 
when the condition is false.  

Like controls, rules are also assigned a priority. 
If rules with conflicting actions should occur at the same time, the rule with the highest priority will override 
all others. The priority argument should be an element of the :class:`~wntr.network.controls.ControlPriority` class. The default 
priority is medium (3). Priority can only be assigned when the rule is created.

The following examples illustrate the creation of rules, using conditions and actions similar to those defined above.

.. doctest::

    >>> cond2 = controls.SimTimeCondition(wn, controls.Comparison.ge, '121:00:00')
    
    >>> rule1 = controls.Rule(cond1, [act1], name='rule1')
    >>> print(rule1)
    IF TANK 1 LEVEL ABOVE 46.0248 THEN PIPE 330 STATUS IS OPEN PRIORITY 3
    
    >>> pri5 = controls.ControlPriority.high
    >>> rule2 = controls.Rule(cond2, [act2], name='rule2', priority=pri5)
    >>> print(rule2)
    IF SYSTEM TIME >= 121:00:00 THEN PUMP 10 STATUS IS OPEN PRIORITY 5

Since rules operate on a different timestep than controls, these rules might behave differently than the equivalent controls defined above. 
Controls (or simple controls in EPANET) operate on the hydraulic timestep while Rules (or rule-based controls in EPANET) operate at a smaller timestep. 
By default, the rule timestep is 1/10th of the hydraulic timestep. It is important to remember that significant differences 
might occur when timesteps are smaller; this applies not only to rule timesteps, but also to hydraulic or quality timesteps.

More complex rules can be written using one of the Boolean logic condition classes.
The following example creates a new rule that will open pipe 330 if both conditions are true, 
and otherwise it will open pump 10. 

.. doctest::
    
    >>> cond3 = controls.AndCondition(cond1, cond2)
    >>> print(cond3)
     TANK 1 LEVEL ABOVE 46.0248 AND SYSTEM TIME >= 121:00:00 
    
    >>> rule3 = controls.Rule(cond3, [act1], [act2], priority=3, name='complex_rule')
    >>> print(rule3)
    IF  TANK 1 LEVEL ABOVE 46.0248 AND SYSTEM TIME >= 121:00:00  THEN PIPE 330 STATUS IS OPEN ELSE PUMP 10 STATUS IS OPEN PRIORITY 3

Actions can also be combined, as shown in the following example.

.. doctest::

    >>> cond4 = controls.OrCondition(cond1, cond2)
    >>> rule4 = controls.Rule(cond4, [act1, act2], name='rule4')
    >>> print(rule4)
    IF  TANK 1 LEVEL ABOVE 46.0248 OR SYSTEM TIME >= 121:00:00  THEN PIPE 330 STATUS IS OPEN AND PUMP 10 STATUS IS OPEN PRIORITY 3

The flexibility of rules provides an extremely powerful tool for defining complex network operations.

Adding controls/rules to a network
------------------------------------

Once a control or rule is created, it can be added to the network.
This is accomplished using the :class:`~wntr.network.model.WaterNetworkModel.add_control` method of the water network model object.
The control or rule should be named so that it can be retrieved and modified if desired.

.. doctest::

    >>> wn.add_control('NewTimeControl', ctrl2)
    >>> wn.get_control('NewTimeControl')
    <Control: 'control2', <SimTimeCondition: model, 'Is', '5-01:00:00', False, 0>, [<ControlAction: 10, status, OPEN>], [], priority=3>

..
	If a control of that name already exists, an error will occur. In this case, the control will need to be deleted first.

	.. doctest::

		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
		ValueError: The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.
		>>> wn.remove_control('NewTimeControl')
		>>> wn.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
