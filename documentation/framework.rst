
.. role:: red

.. raw:: latex

    \clearpage

.. _software_framework:

Software framework and limitations
======================================

Before using WNTR, it is helpful to understand the software framework.
WNTR is a Python package, which contains several subpackages, listed in :numref:`table-wntr-subpackage`.
Each subpackage contains modules that contain classes, methods, and functions. 
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
   :class:`~wntr.network`	                           Contains classes and methods to define a water network model, network controls, model options, and graph representation of the network.
   :class:`~wntr.scenario`                            Contains classes and methods to define disaster scenarios and fragility/survival curves.
   :class:`~wntr.sim`		                           Contains classes and methods to run hydraulic and water quality simulations using the water network model.
   :class:`~wntr.metrics`	                           Contains functions to compute resilience, including hydraulic, water quality, water security, and economic metrics. Methods to compute topographic metrics are included in the wntr.network.graph module.
   :class:`~wntr.morph`	                              Contains methods to modify water network model morphology, including network skeletonization, modifying node coordinates, and splitting or breaking pipes.
   :class:`~wntr.graphics`                            Contains functions to generate graphics.
   :class:`~wntr.epanet`                              Contains EPANET 2.00.12 compatibility class and methods for WNTR.
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
   :class:`~wntr.network.model.WaterNetworkModel`      Class to generate water network models, including methods to read and write EPANET INP files, and access/add/remove/modify network components.  This class links to additional network classes that are listed below to define network components, controls, and model options.
   :class:`~wntr.network.elements.Junction`	          Class to define junctions. Junctions are nodes where links connect. Water can enter or leave the network at a junction.
   :class:`~wntr.network.elements.Reservoir`           Class to define reservoirs. Reservoirs are nodes with an infinite external source or sink.      
   :class:`~wntr.network.elements.Tank`                Class to define tanks. Tanks are nodes with storage capacity.     
   :class:`~wntr.network.elements.Pipe`		          Class to define pipes. Pipes are links that transport water. 
   :class:`~wntr.network.elements.Pump`                Class to define pumps. Pumps are links that increase hydraulic head.
   :class:`~wntr.network.elements.Valve`               Class to define valves. Valves are links that regulate pressure or flow. 
   :class:`~wntr.network.elements.Curve`               Class to define curves. Curves are data pairs representing a relationship between two quantities.  Curves are used to define pump, efficiency, headloss, and volume curves. 
   :class:`~wntr.network.elements.Source`              Class to define sources. Sources define the location and characteristics of a substance injected directly into the network.
   :class:`~wntr.network.elements.Demands`             Class to define multiple demands per junction. Demands are the rate of withdrawal from the network.
   :class:`~wntr.network.elements.Pattern`             Class to define patterns. Demands, reservoir heads, pump schedules, and water quality sources can have patterns associated with them. 
   :class:`~wntr.network.controls.Control`             Class to define controls. Controls define a single action based on a single condition.
   :class:`~wntr.network.controls.Rule`                Class to define rules. Rules can define multiple actions and multiple conditions.
   :class:`~wntr.network.options.Options`              Class to define model options, including the simulation duration and timestep.
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
   :class:`~wntr.sim.epanet.EpanetSimulator`          The EpanetSimulator can run both the EPANET 2.00.12 Programmer's Toolkit [Ross00]_ and EPANET 2.2.0 Programmer's Toolkit [RWTS20]_ to run hydraulic and water quality simulations.  
                                                      EPANET 2.2.0 (which is used by default) includes both demand-driven and pressure dependent analysis, while EPANET 2.00.12 includes only demand-driven analysis. 
                                                      When using the EpanetSimulator, the water network model is written to an EPANET INP file which is used to run an EPANET simulation. This allows the user to run 
                                                      EPANET simulations, while taking advantage of additional analysis options in WNTR. 
    
   :class:`~wntr.sim.core.WNTRSimulator`              The WNTRSimulator uses custom Python solvers to run demand-driven and pressure dependent demand hydraulic simulations and includes models to simulate pipe leaks.
                                                      The simulator includes an algebraic model, which can be extended to simulate additional components or behaviors in water network models.	
                                                      The WNTRSimulator does not perform water quality simulations.

   =================================================  =============================================================================================================================================================================================================================================================================

.. _limitations:
   
Limitations
---------------
Current WNTR limitations include:

* Certain EPANET INP model options are not supported in WNTR, as outlined below.

* Water quality simulations are only available using the EpanetSimulator. 

* Use of the "MAP" file option in EPANET will **not** automatically assign node
  coordinates from that file. 

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

However, **the [LABELS] section cannot be modified/created through the WNTR API**.

While the EpanetSimulator uses all EPANET model options, several model options are not used by the WNTRSimulator.  
Of the EPANET model options that directly apply to hydraulic simulations, **the following options are not supported by the WNTRSimulator**:

* [EMITTERS] section
* D-W and C-M headloss options in the [OPTIONS] section (H-W option is used)
* Accuracy, unbalanced, and emitter exponent from the [OPTIONS] section
* Pump speed in the [PUMPS] section
* Report start and statistics in the [TIMES] section
* PBV and GPV values in the [VALVES] section

**Future development of WNTR will address these limitations.**

.. _discrepancies:

Discrepancies
-------------------------------------------
Known discrepancies between the WNTRSimulator and EpanetSimulator are listed below.

* **Tank draining**: The EpanetSimulator (and EPANET) continue to supply water from tanks after they reach their 
  minimum elevation.  This can result in incorrect system pressures.
  See issues https://github.com/USEPA/WNTR/issues/210 and https://github.com/OpenWaterAnalytics/EPANET/issues/623
  The EPANET dll in WNTR will be updated when an EPANET release is available.
* **Pump controls and patterns**: Pumps have speed settings which are adjustable 
  by controls and/or patterns.  With the EpanetSimulator, 
  controls and patterns adjust the actual speed.  With the WNTRSimulator, pumps have a 'base speed' 
  (similar to junction demand and reservoir head), controls adjust the base speed, and speed patterns are 
  a multiplier on the base speed. Results from the two simulators can match by scaling speed patterns 
  and using controls appropriately.
* **Leak models**: Leak models are only available using the WNTRSimulator.  Emitters can be used to model leaks in EPANET.
* **Multi-point head pump curves**: When using the EpanetSimulator, multi-point 
  head pump curves are created by connecting the points with straight-line segments.  
  When using the WNTRSimulator, the points are fit to the same :math:`H = A - B*Q^C` 
  function that is used for 3-point curves.
* **Variable required pressure, minimum pressure, and pressure exponent**: 
  Junction attributes can be used to assign spatially variable required pressure, minimum pressure, and pressure exponent.  
  These attributes are only used for pressure dependent demand simulation with the WNTRSimulator.  
  If the junction attributes are set to None (the default value), then the required pressure, minimum pressure, and pressure exponent defined in the global hydraulic options (`wn.options.hydraulic`) are used for that junction.
  Pressure dependent demand simulation using the EpanetSimulator always uses values in the global hydraulic options.
* **Pattern Interpolation**: The WNTRSimulator can include pattern interpolation by setting
  :py:class:`wn.options.time.pattern_interpolation
  <wntr.network.options.TimeOptions>`.  If True, 
  interpolation is used to determine pattern values between pattern
  timesteps. If False, the step-like behavior from EPANET is used. 
  Interpolation with a shorter hydraulic timestep can make problems with large changes in patterns (e.g., large changes in demand) easier to solve.
  The default is False.
