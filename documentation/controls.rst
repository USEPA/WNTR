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


.. doctestsetup::

    >>> import wntr
    >>> from __future__ import print_function

.. doctest::

    >>> n1 = wntr.network.model.Junction('N1')
    >>> n2 = wntr.network.model.Junction('N2')
    >>> link = wntr.network.model.Pipe('L1', 'N1', 'N2')
    >>> ctrl = wntr.network.controls.ControlAction(link, 'status', 0)
    >>> print(ctrl)
    set Pipe('L1').status to Closed


