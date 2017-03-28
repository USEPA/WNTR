.. raw:: latex

    \newpage

Water network controls
======================================

One of the key features of EPANET is the ability to control links -- pipes, pumps and valves -- using "controls" and "rules."
The key distinction between the two is that controls are limited to a single action -- closing/opening a link or changing the setting -- based on a single comparison -- time based or tank level based.
An EPANET rule is more complicated; rules take an IF-THEN-ELSE style format and can have multiple conditions and multiple actions in each of the logical blocks.
This section will not go over how to write EPANET controls or rules in detail, please see the EPANET user manual for that information.
WNTR fully supports EPANET's rules and controls sections when reading from and INP file and using the :class:`~wntr.sim.epanet.EpanetSimulator`.
When using the :class:`~wntr.sim.core.WNTRSimulator` there is additional power available within the WNTR controls framework.

Control actions
-----------------------

Control actions tell the simulator what to do when a rule becomes "true." 
These are created using the :class:`~wntr.network.controls.ControlAction` class.
A control action takes a target link, the property to change, and the value to change it to.
The following examples use the test network "Net3.inp" as the initial network.

.. doctest::
    :hide:

    >>> import wntr
    >>> import numpy as np
    >>> from __future__ import print_function
    >>> try:
    ...    net3 = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    net3 = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
    ...
    >>> print(net3)   # doctest: +SKIP
    <WaterNetworkModel object at 0x03978184 >


.. doctest::

    >>> import wntr.network.controls as controls  # for easier documentation
    >>> n1 = net3.get_node('1')
    >>> l1 = net3.get_link('330')
    >>> print([n1, l1])
    [<Tank '1'>, <Pipe '330'>]
    >>> act1 = controls.ControlAction(l1, 'status', 1)
    >>> print(act1)
    set Pipe('330').status to Open


Simple controls
---------------------

Control objects that emulate EPANET's "controls" section entries are available as three classes.
The time based controls are :class:`~wntr.netowrk.controls.TimeControl` objects, and tank level and junction pressure based controls are :class:`~wntr.network.controls.ConditionalControl` objects.
Taking the tank and pipe selected previously, we start to create a control object using the action ``act1`` we created above.
The control will be a :class:`~wntr.network.controls.ConditionalControl` that opens pipe 330 if the level of tank 1 goes above 46.0248 m.
To specify the source -- i.e., the tank level -- we use a tuple composed of the node ``n1`` and the attribute, ``'level'``.
To specify the comparison should be when the level is greater than the threshold, we use the NumPy function ``np.greater``.
The control is created as follows:

.. doctest::

    >>> attr1 = 'level'
    >>> thresh1 = 46.0248
    >>> ctrl1 = controls.ConditionalControl( (n1, attr1), np.greater, thresh1, act1)
    >>> ctrl1
    <ConditionalControl: <Tank '1'>, 'level'), <ufunc 'greater'>, 46.0248, <ControlAction: <Pipe '330'>, 'status', 'Open'>>

To get an EPANET-like description of this control, use the print function.

.. doctest::

    >>> print(ctrl1)
    LINK 330 Open IF NODE 1 Above 46.0248

Now create a time-based control.
The new action will be to open Pump 10 at a specific time, in this case hour 121 of the simulation.
The time flag is either ``'SIM_TIME'`` or ``'SHIFTED_TIME'``; these indicate simulation or clock time, respectively.
The daily flag indicates that the control should be repeated every 24 hours; it should be ``True`` when ``'SHIFTED_TIME'`` is used, and otherwise be false.

.. doctest::

    >>> time2 = 121 * 60 * 60  # time must be in seconds
    >>> timeflag2 = 'SIM_TIME'
    >>> dailyflag2 = False
    >>> pump2 = net3.get_link('10')
    >>> act2 = controls.ControlAction(pump2, 'status', 1)
    >>> ctrl2 = controls.TimeControl( net3, time2, timeflag2, dailyflag2, act2)
    >>> print(ctrl2)
    LINK 10 Open AT TIME 121:00:00

This is one case where there are more options available in the WNTR simulator than in the EPANET simulator.
The EpanetSimulator is limited to the pairs ``(time_flag='SIM_TIME', daily_flag=False)`` and ``(time_flag='SHIFTED_TIME', daily_flag=True)``; any other combination will have undefined results.
The WNTRSimulator can use any combination of the two.


Adding controls to a network
-------------------------------

Once the controls are created, they must be added to the network.
This is accomplished using the :meth:`~wntr.network.model.WaterNetworkModel.add_control` method of the water network model object.
The control should be named so that it can be retrieved and modified if desired.

.. doctest::

    >>> net3.add_control('NewTimeControl', ctrl2)
    >>> net3.get_control('NewTimeControl')
    <TimeControl: model, 435600, 'SIM_TIME', False, <ControlAction: <Pump '10'>, 'status', 'Open'>>


If a control of that name already exists, an error will occur. In this case, the control will need to be deleted first.

.. doctest::

    >>> net3.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP
    ValueError: The name provided for the control is already used. Please either remove the control with that name first or use a different name for this control.
    >>> net3.remove_control('NewTimeControl')
    >>> net3.add_control('NewTimeControl', ctrl2)   # doctest: +SKIP


Rules, complex controls
--------------------------

The two control actions described so far are clearly fairly limited in scope.
EPANET approaches this using the "rules" section of an INP file; WNTR uses an :class:`~wntr.network.controls.IfThenElseControl` object.
An :class:`~wntr.network.controls.IfThenElseControl` is created using a :class:`~wntr.network.controls.ControlCondition` object and a :class:`~wntr.network.controls.ControlAction` object.
The different condition classes available are listed below, along with a short explanation.

.. autosummary::

    ~wntr.network.controls.TimeOfDayCondition
    ~wntr.network.controls.SimTimeCondition
    ~wntr.network.controls.ValueCondition
    ~wntr.network.controls.RelativeCondition
    ~wntr.network.controls.OrCondition
    ~wntr.network.controls.AndCondition


All the above conditions are valid EPANET conditions except :class:`~wntr.network.controls.RelativeCondition`; however, some advanced features of may not be defined.
See the EPANET user manual for the acceptable parameters and attributes for use with EPANET RULES.
An EPANET INP file will create an IfThenElseControl within the water network model for each rule defined.
A very simple example is presented below, showing how the previous examples of controls can be recreated using the IfThenElseControl, instead.

.. doctest::

    >>> cond1 = controls.ValueCondition( n1, 'level', '>', 46.0248)
    >>> print(cond1)
    Tank('1').level > 46.0248
    
    >>> rule1 = controls.IfThenElseControl( cond1, [ act1 ], name='control1' )
    >>> print(rule1)
    Rule control1 := if Tank('1').level > 46.0248 then set Pipe('330').status to Open
    
    >>> cond2 = controls.SimTimeCondition( net3, '=', '121:00:00' )
    >>> print(cond2)
    sim_time = 435600 sec
    
    >>> rule2 = controls.IfThenElseControl( cond2, [ act2 ], name='control2' )
    >>> print(rule2)
    Rule control2 := if sim_time = 435600 sec then set Pump('10').status to Open


These are simple rules. More complex rules can be written using one of the boolean logic condition classes.
To demonstrate, create a new rule that will open pipe 330 if both conditions are true, and otherwise it will open pipe 10; this rule will behave very differently from the rules above.

.. doctest::

    >>> cond3 = controls.AndCondition( cond1, cond2 )
    >>> print(cond3)
    ( Tank('1').level > 46.0248 && sim_time = 435600 sec )
    
    >>> rule3 = controls.IfThenElseControl( cond3, [ act1 ], [ act2 ], priority=3, name='weird')
    >>> print(rule3)
    Rule weird := if ( Tank('1').level > 46.0248 && sim_time = 435600 sec ) then set Pipe('330').status to Open else set Pump('10').status to Open with priority 3

Actions can also be combined.

.. doctest::

    >>> cond4 = controls.OrCondition( cond1, cond2 )
    >>> rule4 = controls.IfThenElseControl( cond4, [act1, act2])
    >>> print(rule4)
    Rule  := if ( Tank('1').level > 46.0248 || sim_time = 435600 sec ) then set Pipe('330').status to Open and set Pump('10').status to Open


The flexibility of the IfThenElseControl combined with the different ControlCondition classes and ControlActions provides an extremely powerful tool for defining network operations based on real-world planning and behaviors.


