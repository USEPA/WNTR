Hydraulic and Water Quality Simulation
======================================

.. todo:: Add background and examples from the Simulation White Paper

Hydraulic simulation
--------------------

* Demand driven (EPANET, Pyomo, Python)
* Pressure driven (Pyomo, Python)
* Pipe break model
* Conditional controls

.. todo:: 

     Add a section to the documentation on tips for users:
          * Place check valves next to reservoirs if you don't want water flowing back into the reservoir
          * Place check bypasses around pumps if you want them.
          * Pipes with large diameters, large roughness coefficients, and small lengths will have small resistance coefficients. If the resistance coefficient is too small, weird things may happen.


Water quality simulation
------------------------

* Concentration
* Water age
* Trace