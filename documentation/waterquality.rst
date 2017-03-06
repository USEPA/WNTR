.. _water_quality_simulation:

Water quality simulation
==================================

Water quality simulation can only be run using the **EpanetSimulator**. 
The example **water_quality_simulation.py** can be used to run water quality simulations and plot results.

As listed in the :ref:`software_framework` section,  this means that the hydraulic simulation must use demand driven simulation.
Note that the WNTRSimulator can be used to compute demands under pressure-driven conditions and those 
demands can be used in the EPANETSimulator.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 50-54
   
After defining water quality options and sources (described in the :ref:`wq_options` and :ref:`sources` sections below), a hydraulic and water quality simulation 
using the EpanetSimualtor is run using the following code.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 7, 14
   
.. _wq_options:

Options
----------
Water quality simulation options are defined in the :meth:`~wntr.network.model.WaterNetworkOptions` class.
Three types of water quality analysis are supported.  These options include water age, tracer, and chemical concentration.

* **Water age**: Water quality simulation can be used to compute water age at every node.
  To compute water age, set the 'quality' option as follows.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 23

* **Tracer**: Water quality simulation can be used to compute the percent of flow originating from a specific location.
  The results include tracer percent values at each node.
  For example, to track a tracer from node '123', set the 'quality' and 'tracer_node' options as follows.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 33, 34

* **Chemical concentration**: Water quality simulation can be used to compute chemical concentration given a set of source injections.
  The results include chemical concentration values at each node.
  To compute chemical concentration, define sources (described in the :ref:`sources` section below) and set the 'quality' options as follows.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 10

* To skip water quality simulation, set the 'quality' options as follows.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 44

Additional water quality options include viscosity, diffusivity, specific gravity, tolerance, bulk reaction order, wall reaction order, 
tank reaction order, bulk reaction coefficient, wall reaction coefficient, limiting potential, and roughness correlation.
These parameters are defined in the in the :meth:`~wntr.network.model.WaterNetworkOptions` documentation.

When creating a water network model from an EPANET INP file, water quality options are populated from the [OPTIONS] and [REACTIONS] sections of EPANET INP file.
All of these options can be modified in WNTR and then written to an EPANET INP file.

.. _sources:

Sources
------------
Sources are required for CHEMICAL water quality analysis.  
Sources are added to the water network model using the :meth:`~wntr.network.model.WaterNetworkModel.add_source` method.
Sources include the following information:

* **Source name**: A unique source name used to reference the source in the water network model.

* **Node name**: The injection node.

* **Source type**: options include 'CONCEN', 'MASS', 'FLOWPACED', or 'SETPOINT'.

  * CONCEN source represents injection of a specific concentration.
  
  * MASS source represents a booster source with fixed mass flow rate. 
  
  * FLOWPACED source represents a booster source with fixed concentration at the inflow of the node.
  
  * SETPOINT source represents a booster source with fixed concentration at the outflow of the node.
  
* **Strength**: Baseline source strength (in mass/time for MASS and mass/volume for CONCEN, FLOWPACED, and SETPOINT).

* **Pattern**: Pattern name

For example, the following code can be used to add a source, and associated pattern, to the water network model.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 11, 12
	
The method :meth:`~wntr.network.model.WaterNetworkModel.remove_source` can be used to remove sources from the water network model.

When creating a water network model from an EPANET INP file, sources that are defined in the [SOURCES] section are added to the water network model.  
These sources are given the name 'INP#' where # is the source number.
