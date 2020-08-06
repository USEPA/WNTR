.. raw:: latex

    \clearpage

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
	
.. _water_quality_simulation:
	
Water quality simulation
==================================

Water quality simulations can only be run using the EpanetSimulator. 
As listed in the :ref:`software_framework` section,  this means that the hydraulic simulation must use demand-driven simulation.
The WNTRSimulator can be used to compute demands under pressure dependent demand conditions and those 
demands can be used in the EpanetSimulator (see :ref:`wq_pdd` below).
 
.. note:: 
  The hydraulic simulation limitation is due to WNTR currently using EPANET 2.00.12, and not the currently released EPANET 2.2.0 with the pressure dependent algorithm. 
 
After defining water quality options and sources (described in the :ref:`wq_options` and :ref:`sources` sections below), a hydraulic and water quality simulation 
using the EpanetSimulator is run using the following code:

.. doctest::

    >>> import wntr # doctest: +SKIP
	
    >>> wn = wntr.network.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP
    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> results = sim.run_sim()

The results include a quality value for each node (see :ref:`simulation_results` for more details).

.. _wq_options:

Options
----------
Water quality simulation options are defined in the :class:`~wntr.network.options.WaterNetworkOptions` class.
Three types of water quality analysis are supported.  These options include water age, tracer, and chemical concentration.

* **Water age**: A water quality simulation can be used to compute water age at every node.
  To compute water age, set the 'quality' option as follows:

  .. doctest::

      >>> wn.options.quality.mode = 'AGE'
	
* **Tracer**: A water quality simulation can be used to compute the percent of flow originating from a specific location.
  The results include tracer percent values at each node.
  For example, to track a tracer from node '111,' set the 'quality' and 'tracer_node' options as follows:

  .. doctest::

      >>> wn.options.quality.mode = 'TRACE'
      >>> wn.options.quality.trace_node = '111'

* **Chemical concentration**: A water quality simulation can be used to compute chemical concentrations given a set of source injections.
  The results include chemical concentration values at each node.
  To compute chemical concentrations, set the 'quality' options as follows:

  .. doctest::

      >>> wn.options.quality.mode = 'CHEMICAL'
	
  The initial concentration is set using the `initial_quality` parameter on each node.  
  This parameter can also be set using the [QUALITY] section of the INP file. 
  The user can also define sources (described in the :ref:`sources` section below).

* To skip the water quality simulation, set the 'quality' options as follows:

  .. doctest::

      >>> wn.options.quality.mode = 'NONE'

Additional water quality options include viscosity, diffusivity, specific gravity, tolerance, bulk reaction order, wall reaction order, 
tank reaction order, bulk reaction coefficient, wall reaction coefficient, limiting potential, and roughness correlation.
These parameters are defined in the :class:`~wntr.network.options.WaterNetworkOptions` API documentation.

When creating a water network model from an EPANET INP file, water quality options are populated from the [OPTIONS] and [REACTIONS] sections of the EPANET INP file.
All of these options can be modified in WNTR and then written to an EPANET INP file.

.. _sources:

Sources
------------
Sources are required for CHEMICAL water quality analysis.  
Sources can still be defined, but *will not* be used if AGE, TRACE, or NONE water quality analysis is selected.
Sources are added to the water network model using the :class:`~wntr.network.model.WaterNetworkModel.add_source` method.
Sources include the following information:

* **Source name**: A unique source name used to reference the source in the water network model.

* **Node name**: The injection node.

* **Source type**: Options include 'CONCEN,' 'MASS,' 'FLOWPACED,' or 'SETPOINT.'

  * CONCEN source represents injection of a specific concentration.
  
  * MASS source represents a booster source with a fixed mass flow rate. 
  
  * FLOWPACED source represents a booster source with a fixed concentration at the inflow of the node.
  
  * SETPOINT source represents a booster source with a fixed concentration at the outflow of the node.
  
* **Strength**: Baseline source strength (in mass/time for MASS and mass/volume for CONCEN, FLOWPACED, and SETPOINT).

* **Pattern**: The pattern name associated with the injection.

For example, the following code can be used to add a source, and associated pattern, to the water network model:

.. doctest::

    >>> source_pattern = wntr.network.elements.Pattern.binary_pattern('SourcePattern', 
    ...       start_time=2*3600, end_time=15*3600, duration=wn.options.time.duration,
    ...       step_size=wn.options.time.pattern_timestep)
    >>> wn.add_pattern('SourcePattern', source_pattern)
    >>> wn.add_source('Source', '121', 'SETPOINT', 1000, 'SourcePattern')

In the above example, the pattern is given a value of 1 between 2 and 15 hours, and 0 otherwise.
The method :class:`~wntr.network.model.WaterNetworkModel.remove_source` can be used to remove sources from the water network model.

Once a source has been added, it can be examined or modified.

.. doctest::

    >>> source = wn.get_source('Source')
    >>> print(source)                                                                                           
    <Source: 'Source', '121', 'SETPOINT', 1000, SourcePattern>

    >>> source.strength_timeseries.base_value = 1500
    >>> print(source)
    <Source: 'Source', '121', 'SETPOINT', 1500, SourcePattern>

When creating a water network model from an EPANET INP file, the sources that are defined in the [SOURCES] section are added to the water network model.  
These sources are given the name 'INP#' where # is an integer related to the number of sources in the INP file.

.. _wq_pdd:

Using PDD
------------

As noted in the :ref:`software_framework` section, a pressure dependent demand hydraulic simulation is only available using the WNTRSimulator
and water quality simulations are only available using the EpanetSimulator.
The following example illustrates how to use pressure dependent demands in a water 
quality simulation.  A hydraulic simulation is first run using the WNTRSimulator in PDD mode.
The resulting demands are used to reset demands in the WaterNetworkModel and hydraulics and
water quality are run using the EpanetSimulator.

.. doctest::

    >>> sim = wntr.sim.WNTRSimulator(wn, 'PDD')
    >>> results = sim.run_sim()

    >>> wn.assign_demand(results.node['demand'].loc[:,wn.junction_name_list], 'PDD')
	
    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> wn.options.quality.mode = 'TRACE'
    >>> wn.options.quality.trace_node = '111'
    >>> results_withPDD = sim.run_sim()
	