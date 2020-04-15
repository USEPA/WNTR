
.. role:: red

.. raw:: latex

    \clearpage

.. _software_framework:

Software framework and limitations
======================================

Before using WNTR, it is helpful to understand the software framework.
WNTR is a Python package, which contains several subpackages, listed in :numref:`table-wntr-subpackage`.
Each subpackage contains modules which contain classes, methods, and functions. 
The classes used to generate water network models and 
run simulations are described in more detail below, followed by a list of software limitations.

.. only:: html

   See :ref:`api_documentation` for more information on the code structure.

.. only:: latex

   See the online API documentation at https://wntr.readthedocs.io for more information on the code structure.
   
.. _table-wntr-subpackage:
.. table:: WNTR Subpackages
   
   =================================================  =============================================================================================================================================================================================================================================================================
   Subpackage                                         Description
   =================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.network`	                          Contains methods to define a water network model, network controls, model options, and graph representation of the network.
   :class:`~wntr.scenario`                            Contains methods to define disaster scenarios and fragility/survival curves.
   :class:`~wntr.sim`		                          Contains methods to run hydraulic and water quality simulations using the water network model.
   :class:`~wntr.metrics`	                          Contains methods to compute resilience, including hydraulic, water quality, water security, and economic metrics. Methods to compute topographic metrics are included in the wntr.network.graph module.
   :class:`~wntr.morph`	                              Contains methods to modify water network model morphology, including network skeletonization, modifying node coordinates, and splitting or breaking pipes.
   :class:`~wntr.graphics`                            Contains methods to generate graphics.
   :class:`~wntr.epanet`                              Contains EPANET 2.0 compatibility functions for WNTR.
   :class:`~wntr.utils`                               Contains helper functions.
   =================================================  =============================================================================================================================================================================================================================================================================

Water network model
----------------------
The :class:`~wntr.network` subpackage contains classes to define the water network model, network controls, and graph representation of the network.
These classes are listed in :numref:`table-network-subpackage`.
Water network models can be built from scratch or built directly from EPANET INP files.
Additionally, EPANET INP files can be generated from water network models.

.. _table-network-subpackage:
.. table:: Network Classes

   ==================================================  =============================================================================================================================================================================================================================================================================
   Class                                               Description
   ==================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.network.model.WaterNetworkModel`      Contains methods to generate water network models, including methods to read and write EPANET INP files, and access/add/remove/modify network components.  This class links to additional model classes (below) which define network components, controls, and model options.
   :class:`~wntr.network.elements.Junction`	           Contains methods to define junctions. Junctions are nodes where links connect. Water can enter or leave the network at a junction.
   :class:`~wntr.network.elements.Reservoir`           Contains methods to define reservoirs. Reservoirs are nodes with an infinite external source or sink.      
   :class:`~wntr.network.elements.Tank`                Contains methods to define tanks. Tanks are nodes with storage capacity.     
   :class:`~wntr.network.elements.Pipe`		           Contains methods to define pipes. Pipes are links that transport water. 
   :class:`~wntr.network.elements.Pump`                Contains methods to define pumps. Pumps are links that increase hydraulic head.
   :class:`~wntr.network.elements.Valve`               Contains methods to define valves. Valves are links that limit pressure or flow. 
   :class:`~wntr.network.elements.Curve`               Contains methods to define curves. Curves are data pairs representing a relationship between two quantities.  Curves are used to define pump curves. 
   :class:`~wntr.network.elements.Source`              Contains methods to define sources. Sources define the location and characteristics of a substance injected directly into the network.
   :class:`~wntr.network.elements.Demands`             Contains methods to define multiple demands per junction. Demands are the rate of withdrawal from the network.
   :class:`~wntr.network.elements.Pattern`             Contains methods to define patterns. Demands, reservoir heads, pump schedules, and water quality sources can have patterns associated with them. 
   :class:`~wntr.network.controls.Control`             Contains methods to define controls. Controls define a single action based on a single condition.
   :class:`~wntr.network.controls.Rule`                Contains methods to define rules. Rules can define multiple actions and multiple conditions.
   :class:`~wntr.network.options.WaterNetworkOptions`  Contains methods to define model options, including the simulation duration and time step.
   ==================================================  =============================================================================================================================================================================================================================================================================

Simulators
---------------
The :class:`~wntr.sim` subpackage contains classes to run hydraulic and water quality simulations using the water network model.
WNTR contains two simulators: the EpanetSimulator and the WNTRSimulator.
These classes are listed in :numref:`table-sim-subpackage`.

.. _table-sim-subpackage:
.. table:: Simulator Classes

   =================================================  =============================================================================================================================================================================================================================================================================
   Class                                              Description
   =================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.sim.epanet.EpanetSimulator`          The EpanetSimulator uses the EPANET 2.0 Programmer's Toolkit [Ross00]_ to run demand-driven hydraulic simulations and water quality simulations.
                                                      When using the EpanetSimulator, the water network model is written to an EPANET INP file which is used to run an EPANET simulation.
                                                      This allows the user to read in EPANET INP files, modify the model, run 
                                                      an EPANET simulation, and analyze results all within WNTR.
	
	:class:`~wntr.sim.core.WNTRSimulator`             The WNTRSimulator uses custom Python solvers to run demand-driven and pressure dependent demand hydraulic simulations and includes models to simulate pipe leaks. 
	                                                  The WNTRSimulator does not perform water quality simulations, however, the hydraulic simulation results can be used with the EpanetSimulator to perform water quality simulations. See :ref:`water_quality_simulation` for an example.
   =================================================  =============================================================================================================================================================================================================================================================================

.. _limitations:
   
Limitations
---------------
Current software limitations are noted:

* Certain EPANET INP model options are not supported in WNTR, as outlined below.

* Pressure dependent demand hydraulic simulation and leak models are only available using the WNTRSimulator.  

* Water quality simulations are only available using the EpanetSimulator.  

**WNTR reads in and writes all sections of EPANET INP files**.  This includes the following sections: 
[BACKDROP], 
[CONTROLS], 
[COORDINATES], 
[CURVES], 
[DEMANDS],
[EMITTERS],
[ENERGY],
[JUNCTIONS],
[LABELS],
[MIXING],
[OPTIONS],
[PATTERNS],
[PIPES],
[PUMPS],
[QUALITY],
[REACTIONS],
[REPORT],
[RESERVOIRS],
[RULES],
[SOURCES],
[TAGS],
[TANKS],
[TIMES],
[TITLE],                                  
[VALVES], and
[VERTICES].  

However, **the following model options cannot be modified/created through the WNTR API**:

* [EMITTERS] section
* [LABELS] section
* [MIXING] section

While the EpanetSimulator uses all EPANET model options, several model options are not used by the WNTRSimulator.  
Of the EPANET model options that directly apply to hydraulic simulations, **the following options are not supported by the WNTRSimulator**:

* [EMITTERS] section
* D-W and C-M headloss options in the [OPTIONS] section (H-W option is used)
* Accuracy, unbalanced, and emitter exponent from the [OPTIONS] section
* Multipoint curves in the [CURVES] section (3-point curves are supported)
* Pump speed in the [PUMPS] section
* Volume curves in the [TANKS] section
* Pattern start, report start, start clocktime, and statistics in the [TIMES] section
* PBV and GPV values in the [VALVES] section

**Future development of WNTR will address these limitations.**

.. _discrepancies:

Discrepancies
-------------------------------------------
Known discrepancies between the WNTRSimulator and EpanetSimulator are listed below.

* Pumps have speed settings which are adjustable by controls and/or patterns.  With the EpanetSimulator, 
  controls and patterns adjust the actual speed.  With the WNTRSimulator, pumps have a 'base speed' 
  (similar to junction demand and reservoir head), controls adjust the base speed, and speed patterns are 
  a multiplier on the base speed. Results from the two simulators can match by scaling speed patterns 
  and using controls appropriately.
