.. _water_quality_simulation:

Water quality simulation
==================================

Water quality simulation can be run using the EpanetSimulator.  
Water quality scenarios are defined using the class :doc:`Waterquality</apidoc/wntr.scenario.Waterquality>`.
This class stores information on the water quality type and injection.  
EPANET supports water quality simulation to track chemical concentration, 
water age, and tracer percent.
The example **water_quality_simulation.py** can be used to run water quality simulations and plot results.

The following code can be used to run a hydraulic and water quality simulation, 
in this case, to compute water age.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 7, 20-21

Concentration
-------------
If water quality type is set to 'CHEM', then the EpanetSimulator computes chemical concentration.
The user must supply the injection node(s), source type, quality, start and end time.
Concentration is stored in ``results.node['quality']``.

Water age
---------
If water quality type is set to 'AGE', then the EpanetSimulator computes water age.  No other 
input parameters are needed.
Water age is stored in ``results.node['quality']``.

Tracer
------
If water quality type is set to 'TRACE', then the EpanetSimulator tracks the chemical as a tracer and 
reports the percent of flow originating from a specific location.
The user must supply the injection node(s).
Tracer percent is stored in ``results.node['quality']``.