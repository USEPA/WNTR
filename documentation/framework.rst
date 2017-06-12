
.. role:: red

.. raw:: latex

    \clearpage

.. _software_framework:

Software framework and limitations
======================================

Before using WNTR, it is helpful to understand the software framework.
WNTR is a python package, which contains several object-oriented subpackages, listed in :numref:`table-wntr-subpackage`.
Each subpackage contains modules which contain classes, methods, and functions.
See :ref:`api_documentation` for more information on the code structure.
The classes used to generate water network models and 
run simulations are described in more detail below, followed by a list of software limitations.

.. _table-wntr-subpackage:
.. table:: WNTR subpackages.
   
   =================================================  =============================================================================================================================================================================================================================================================================
   Subpackage                                         Description
   =================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.epanet`                              Contains EPANET2 compatibility functions for WNTR.
   :class:`~wntr.metrics`	                          Contains methods to compute resilience, including hydraulic, water quality, water security, and economic metrics. Methods to compute topographic metrics are included in the wntr.network.graph module.
   :class:`~wntr.network`	                          Contains methods to define a water network model, network controls, and graph representation of the network.
   :class:`~wntr.scenario`                            Contains methods to define disaster scenarios and fragility/survival curves.
   :class:`~wntr.sim`		                          Contains methods to run hydraulic and water quality simulations using the water network model.
   :class:`~wntr.graphics`                            Contains methods to generate graphics.
   :class:`~wntr.utils`                               Contains helper functions.
   =================================================  =============================================================================================================================================================================================================================================================================

Water network model
----------------------
The :class:`~wntr.network` subpackage contains classes to define the water network model, network controls, and graph representation of the network.
These classes are listed in :numref:`table-network-subpackage`.
Water network models can be built from scratch or built directly from EPANET INP files.
Additionally, EPANET INP files can be generated from water network models.

.. _table-network-subpackage:
.. table:: Classes in the network subpackage.

   ==================================================  =============================================================================================================================================================================================================================================================================
   Class                                               Description
   ==================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.network.model.WaterNetworkModel`      Contains methods to generate water network models, including methods to read and write INP files, and access/add/remove/modify network components.  This class links to additional model classes (below) which define network components, controls and model options.
   :class:`~wntr.network.model.Junction`	           Contains methods to define junctions. Junctions are nodes where links connect. Water can enter or leave the network at a junction.
   :class:`~wntr.network.model.Reservoir`              Contains methods to define reservoirs. Reservoirs are nodes with an infinite external source or sink.      
   :class:`~wntr.network.model.Tank`                   Contains methods to define tanks. Tanks are nodes with storage capacity.     
   :class:`~wntr.network.model.Pipe`		           Contains methods to define pipes. Pipes are links that transport water. 
   :class:`~wntr.network.model.Pump`                   Contains methods to define pumps. Pumps are links that increase hydraulic head.
   :class:`~wntr.network.model.Energy`                 Contains attributes for specifying global energy prices and global pump efficiencies.
   :class:`~wntr.network.model.Valve`                  Contains methods to define valves. Valves are links that limit pressure or flow. 
   :class:`~wntr.network.model.Curve`                  Contains methods to define curves. Curves are data pairs representing a relationship between two quantities.  Curves are used to define pump curves. 
   :class:`~wntr.network.model.Source`                 Contains methods to define sources. Sources define the location and characteristics of a substance injected directly into the network.
   :class:`~wntr.network.controls.TimeControl`         Contains methods to define time controls. Time controls define actions that start or stop at a particular time. 
   :class:`~wntr.network.controls.ConditionalControl`  Contains methods to define conditional controls. Conditional controls define actions that start or stop based on a particular condition in the network. 
   :class:`~wntr.network.model.WaterNetworkOptions`    Contains methods to define model options, including the simulation duration and time step.
   ==================================================  =============================================================================================================================================================================================================================================================================

Simulators
---------------
The :class:`~wntr.sim` subpackage contains classes to run hydraulic and water quality simulations using the water network model.
WNTR contains two simulators: the EpanetSimulator and the WNTRSimulator.
These classes are listed in :numref:`table-sim-subpackage`.

.. _table-sim-subpackage:
.. table:: Classes in the sim subpackage.

   =================================================  =============================================================================================================================================================================================================================================================================
   Class                                              Description
   =================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.sim.epanet.EpanetSimulator`          The EpanetSimulator uses the EPANET 2 Programmer's Toolkit [Ross00]_ to run demand-driven hydraulic simulation and water quality simulation.
                                                      When using the EpanetSimulator, the water network model is written to an EPANET INP file which is used to run an EPANET simulation.
                                                      This allows the user to read in INP files, modify the model, run 
                                                      an EPANET simulation, and analyze results all within WNTR.
	
	:class:`~wntr.sim.core.WNTRSimulator`             The WNTRSimulator uses custom python solvers to run demand-driven and pressure-driven hydraulic simulation and includes models to simulate pipe leaks. 
	                                                  The WNTRSimulator does not perform water quality simulation.
   =================================================  =============================================================================================================================================================================================================================================================================

.. _limitations:
   
Limitations
---------------
Current software limitations are noted:

* Certain EPANET INP model options are not supported in WNTR, as outlined below.

* Pressure-driven hydraulic simulation and leak models are only available using the WNTRSimulator.  

* Water quality simulation is only available using the EpanetSimulator.  

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

However, **the following model options cannot be modified/created in WNTR**:

* [BACKDROP] section
* Efficiency curves in the [CURVES] section
* [DEMANDS] section (base demand and patterns from the [JUNCTIONS] section can be modified)
* [EMITTERS] section
* [LABELS] section
* [MIXING] section
* [REPORT] section
* [VERTICES] section

While the EpanetSimulator uses all EPANET model options, several model options are not used by the WNTRSimulator.  
Of the EPANET model options that directly apply to hydraulic simulation, **the following options are not supported by the WNTRSimualtor**:

* [DEMANDS] section (base demand and patterns from the [JUNCTIONS] section are used)
* [EMITTERS] section
* D-W and C-M headloss options in the [OPTIONS] section (H-W option is used)
* Accuracy, unbalanced, demand multiplier, and emitter exponent from the [OPTIONS] section
* Speed option and multipoint head curves in the [PUMPS] section (3-point head curves are supported)
* Head pattern option in the [RESERVOIRS] section
* Volume curves in the [TANKS] section
* Rule timestep, pattern start, report start, start clocktime, and statistics in the [TIMES] section
* PSV, FCV, PBV, GPV values in the [VALVES] section

**Future development of WNTR will address these limitations.**
