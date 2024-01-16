
.. role:: red

.. raw:: latex

    \clearpage

.. doctest::
    :hide:
    
    >>> import wntr.stormwater as swntr
    >>> try:
    ...    swn = swntr.network.StormWaterNetworkModel('../examples/networks/Site_Drainage_Model.inp')
    ... except:
    ...    swn = swntr.network.StormWaterNetworkModel('examples/networks/Site_Drainage_Model.inp')
	
.. _stormwater:

Stormwater/Wastewater resilience analysis
=========================================
.. note:: 
   Stormwater and wastewater resilience capabilities in WNTR are new
   and should be considered beta software. Feedback is appreciated.

Overview 
---------
The following section describes capabilities in WNTR to 
quantify the resilience of stormwater and wastewater systems.  
This capability resides in the :class:`~wntr.stormwater` subpackage.
This subpackage is intended to 
leverage existing stormwater and wastewater analysis packages within a framework that 
facilitates the use of WNTR resilience capabilities.
For that reason, **familiarity with WNTR is recommended before using the stormwater subpackage**.
Drinking water functionality in WNTR is cross referenced in 
this section to provide additional background.

WNTR's stormwater subpackage uses EPA's `Storm Water Management Model (SWMM) <https://www.epa.gov/water-research/storm-water-management-model-swmm>`_ :cite:p:`ross22`
through the use of two Python packages managed by the `pyswmm organization <https://www.pyswmm.org>`_.
This includes: 

* **pyswmm** :cite:p:`pyswmm`: used to run SWMM hydraulic simulations, https://github.com/pyswmm/pyswmm
* **swmmio** :cite:p:`swmmio`: used to access and modify SWMM INP files, https://github.com/pyswmm/swmmio

Select WNTR classes/methods/functions that were developed for drinking water 
resilience analysis are imported into the stormwater subpackage to provide capabilities for 
stormwater and wastewater resilience analysis.

The subpackage is intended to be used a standalone package.
In the examples below, the stormwater subpackage is imported as "swntr" (pronounced "S-winter").

.. doctest::

    >>> import wntr.stormwater as swntr

The stormwater subpackage includes the following modules:

.. _table-wntr-stormwater-modules:
.. table:: WNTR Stormwater Modules
   
   =================================================  =============================================================================================================================================================================================================================================================================
   Module                                             Description
   =================================================  =============================================================================================================================================================================================================================================================================
   :class:`~wntr.stormwater.gis`	                  Contains methods to integrate geospatial data into the model and analysis.
   :class:`~wntr.stormwater.graphics`                 Contains methods to generate graphics.
   :class:`~wntr.stormwater.io`	                      Contains methods to read and write stormwater network models different data formats.
   :class:`~wntr.stormwater.metrics`	              Contains methods to compute resilience, including topographic and hydraulic metrics.
   :class:`~wntr.stormwater.network`	              Contains methods to define stormwater network models.
   :class:`~wntr.stormwater.scenario`                 Contains methods to define fragility/survival curves.
   :class:`~wntr.stormwater.sim`		              Contains methods to run hydraulic simulations.
   =================================================  =============================================================================================================================================================================================================================================================================

Installation
-------------

Follow WNTR's :ref:`installation` instructions to install the stormwater subpackage.

Units
------

While WNTR uses SI units for all drinking water models and analysis (see :ref:`units`), 
**stormwater and wastewater models are not converted to SI units** when loaded into the stormwater subpackage.
Therefore, any additional data used in analysis should match the units of the model.

For reference, :numref:`table-swmm-units` includes SWMM unit conventions :cite:p:`ross22`.  

.. _table-swmm-units:
.. table:: SWMM INP File Unit Conventions

   +----------------------+-------------------------------------+------------------------------------+
   |   Parameter          |   US customary units                |   SI-based units                   |
   +======================+=====================================+====================================+
   |Area (Subcatchment)   |  acres                              |  hectares                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Area (Storage Unit)  |  square feet                        |  square meters                     |
   +----------------------+-------------------------------------+------------------------------------+
   | Area (Ponding)       |  square feet                        |  square meters                     |
   +----------------------+-------------------------------------+------------------------------------+
   | Capillary Suction    |  inches                             |  millimeters                       |
   +----------------------+-------------------------------------+------------------------------------+
   | Concentration        | - mg/L (milligrams/liter)           | - mg/L                             |
   |                      | - ug/L (micrograms/liter)           | - ug/L                             |
   |                      | - #/L (counts/liter)                | - #/L                              |
   +----------------------+-------------------------------------+------------------------------------+
   | Decay Constant       | 1/hours                             | 1/hours                            |
   | (Infiltration)       |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Decay Constant       | 1/days                              | 1/days                             |
   | (Pollutants)         |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Depression Storage   |  inches                             |  millimeters                       |
   +----------------------+-------------------------------------+------------------------------------+
   | Depth                | feet                                | meters                             |
   +----------------------+-------------------------------------+------------------------------------+
   | Diameter             | feet                                | meters                             |
   +----------------------+-------------------------------------+------------------------------------+
   | ...                  |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
 
   
Stormwater network model
------------------------

A stormwater network model can be created directly from SWMM INP files. 
The model is stored in a
:class:`~wntr.stormwater.network.model.StormWaterNetworkModel` object.  

.. doctest::
	
    >>> swn = swntr.network.StormWaterNetworkModel('networks/Site_Drainage_Model.inp') # doctest: +SKIP

.. note::
    The stormwater examples in this section all use Site_Drainage_Model.inp 
    to build the StormWaterNetworkModel, named ``swn``.

DataFrames
^^^^^^^^^^^^^^

The StormWaterNetworkModel includes the following DataFrames which store model attributes:

* ``swn.junctions``
* ``swn.outfalls``
* ``swn.storage``
* ``swn.conduits``
* ``swn.weirs``
* ``swn.orifices``
* ``swn.pumps``
* ``swn.subcatchments``
* ``swn.options``


For example, ``swn.junctions`` contains the following attributes:

.. doctest::
	
    >>> swn.junctions # doctest: +SKIP
          InvertElev  MaxDepth  InitDepth  SurchargeDepth  PondedArea
    Name
    J1        4973.0         0          0               0           0
    J2        4969.0         0          0               0           0
    J3        4973.0         0          0               0           0
    J4        4971.0         0          0               0           0
    J5        4969.8         0          0               0           0
    J6        4969.0         0          0               0           0
    J7        4971.5         0          0               0           0
    J8        4966.5         0          0               0           0
    J9        4964.8         0          0               0           0
    J10       4963.8         0          0               0           0
    J11       4963.0         0          0               0           0

The attributes in these DataFrames can be modified by the user.  
The udpated model is used in hydraulic simulation and analysis.

The StormWaterNetworkModel object also includes methods to return a list of 
junction names, conduits names, etc. 

.. doctest::
	
    >>> swn.conduit_name_list
    ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11']
	
.. note:: 
   :class:`~wntr.stormwater.network.model.StormWaterNetworkModel` uses ``swmmio.Model`` to 
   read and write the SWMM INP file. 
   swimmio stores this information in pandas and geopandas data formats.
  
Hydraulic simulation
---------------------

Hydraulic simulations are run using the 
:class:`~wntr.stormwater.sim.SWMMSimulator` class. Simulation results are stored in a series of 
pandas DataFrames, as described in the following section.

.. doctest::
	
    >>> sim = swntr.sim.SWMMSimulator(swn) 
    >>> results = sim.run_sim()

Overland flow
^^^^^^^^^^^^^^
Overland flow is an important aspect of resilience analysis for stormwater and wastewater systems. 
While SWMM accounts for ponded volume and flooding loss, which account for flood impacts 
at the discharge node, SWMM does not support 1D or 2D overland flow.  
Open source and commercial software tools like GisToSWMM5 and PCSWMM are able to generate 2D overland 
meshes that can be stored in SWMM INP files and run using SWMM.

To include overland flow in stormwater subpackage of WNTR, 
the user should first modify their INP file to include a 1D or 2D overland flow pipes.

.. note:: 
   :class:`~wntr.stormwater.sim.SWMMSimulator` uses ``pyswmm.Simulation`` to run the full
   duration of the SWMM simulation. pyswmm can be used directly for stepwise simulation.

Simulation results
^^^^^^^^^^^^^^^^^^^

Simulation results are stored in a 
:class:`~wntr.stormwater.sim.ResultsObject`. 
Results include timeseries of attributes for 
nodes, links, and subcatchments. 
Each attribute is stored in a pandas DataFrame.
See drinking water documentation on :ref:`simulation_results` for more information on the format of simulation results in WNTR.

Node results include the following attributes for junctions, outfall, and storage nodes:

* Invert depth
* Hydraulic head
* Ponded volume
* Lateral inflow
* Total inflow
* Flooding loss
* Pollution concentration

Link results include the following attributes for conduits, weirs, orifices, and pumps:

* Flow rate
* Flow depth
* Flow velocity
* Capacity
* Pollution concentration

Subcatchment results include the following attributes:

* Rainfall
* Snow depth
* Evaporation loss
* Infill loss
* Runoff rate
* Groundwater outflow rate
* Groundwater table elevation
* Soil moisture
* Pollution concentration

The following example lists node attributes (Note that attribute names use all caps with an underscore between words)

.. doctest::
	
    >>> print(results.node.keys())
    dict_keys(['INVERT_DEPTH', 'HYDRAULIC_HEAD', 'PONDED_VOLUME', 'LATERAL_INFLOW', 'TOTAL_INFLOW', 'FLOODING_LOSSES', 'POLLUT_CONC_0'])

The following example extracts the 'C0' conduit capacity from simulation results.

.. doctest::
	
    >>> conduit_capacity = results.link['CAPACITY'].loc[:, 'C0'] # doctest: +SKIP

Simulation summary
^^^^^^^^^^^^^^^^^^^


Model transformation  and file I/O
----------------------------------

The stormwater subpackage includes the following functions to read/write files and transform 
the StormWaterNetworkModel to other data formats.
This functionality builds on methods in swmmio.

* class:`~wntr.stormwater.io.read_inpfile`: Create a StormWaterNetworkModel object from a SWMM INP file 
* class:`~wntr.stormwater.io.write_inpfile`: Write a SWMM INP file from a StormWaterNetworkModel
* class:`~wntr.stormwater.io.to_graph`: Convert a StormWaterNetworkModel object into a NetworkX graph object
* class:`~wntr.stormwater.io.to_gis`: Convert a StormWaterNetworkModel object into a WaterNetworkGIS object
* class:`~wntr.stormwater.io.read_rptfile`: Create a summary dictionary from a SWMM report file
* class:`~wntr.stormwater.io.read_outfile`: Create SimulationResults object from a SWMM binary output file
* class:`~wntr.stormwater.io.write_geojson`: Create geojson files from a StormWaterNetworkModel object

Disaster scenarios
------------------

Several damage scenarios can be used to quantify resilience of the 
stormwater/wastewater systems, this includes:

* Long term power outages: Power outages impact pumps and lift stations
* Extreme rainfall events: Increased runoff impacts combined stormwater/wastewater systems
* Conduit blockage or collapse: Failure impacts flowrate at the conduit

See :ref:`stormwater_examples` below.

Disaster scenarios can be defined through the use of site and hazard specific GIS data and fragility curves
or using threat agnostic criticality analysis.

Geospatial capabilities
^^^^^^^^^^^^^^^^^^^^^^^^

Site and hazard specific GIS data can be used to define disaster scenarios by 
through the use of geospatial capabilities which allow the user to identify 
components which intersect areas impacted by a disruptive events.
For example, GIS data that defines landslide potential can be used to identify 
conduits that are likely to experience damage from a landslide and fragility curves
define the probability the conduit is damaged as a function of displacement.

The stormwater subpackage includes a :class:`~wntr.stormwater.gis` module which 
facilitates the use of GIS data in geospatial operations, like 
:class:`~wntr.stormwater.gis.snap` and :class:`~wntr.stormwater.gis.intersect`.

The :class:`~wntr.stormwater.network.StormWaterNetworkModel` can be converted into a 
:class:`~wntr.stormwater.gis.WaterNetworkGIS` object, as shown below.

.. doctest::
	
    >>> swn_gis = swn.to_gis(crs)

See drinking water documentation on :ref:`geospatial` for more information.

Fragility curves
^^^^^^^^^^^^^^^^^

Fragility curves are used within disaster scenarios to define the probability that a
component fails for a specific environmental change.  For example, fragility curves can define the 
probability of conduit collapse as a function of peak ground acceleration from an earthquake, or the 
probability of damage to a pump station as a function of flood stage.

:numref:`fig-fragility2` illustrates the fragility curve as a function of peak ground acceleration.  
For example, if the peak ground acceleration is 0.3 at 
a specific pipe, the probability of exceeding a Major damage state is 0.16 and the probability
of exceeding the Minor damage state is 0.80.  

.. _fig-fragility2:
.. figure:: figures/fragility_curve.png
   :width: 640
   :alt: Fragility curve

   Example fragility curve.
   
See drinking water documentation on :ref:`fragility_curves` for more information.

Criticality analysis
^^^^^^^^^^^^^^^^^^^^^

In cases where a specific disaster scenario is not included in the analysis, 
a series of simulations can be used to perform N-k contingency analysis, 
where N is the number of elements and k elements fail.
N-1 contingency analysis is commonly called criticality analysis :cite:p:`wawc06`
and uses a series of simulations to impart damage to one component at a time.
In stormwater and wastewater systems, the analysis can include the following:

* Conduit criticality
* Pump criticality

See drinking water documentation on :ref:`criticality` for more information.

Resilience metrics
-------------------

Resilience of stormwater and wastewater distribution systems depends on many factors, including the 
design, maintenance, and operations of that system. For that reason, the WNTR stormwater module 
includes several metrics to help quantify resilience.  
Additional metrics could also be added at a later date.

Topographic metrics
^^^^^^^^^^^^^^^^^^^^^
Topographic metrics, based on graph theory, can be used to assess the connectivity 
of stormwater and wastewater systems. Many metrics can be computed directly using NetworkX.
See drinking water documentation on :ref:`topographic_metrics` for more information.

The StormWaterNetworkModel can be converted to a NetworkX graph as shown below:

.. doctest::
	
    >>> G = swn.to_graph()

.. note:: 
   The :class:`~wntr.stormwater.network.StormWaterNetworkModel.to_graph` method uses ``swmmio.Model`` to 
   create the NetworkX graph object.  The WNTR methods includes additional options to add node and link weight, and 
   modify the direction of links according to the sign of the link weight (generally flow direction).

The graph can be used in NetworkX functions to compute network topographic metrics. 
Example topographic metrics include:

* Node degree
* Betweenness centrality
* Shortest path length
* Segmentation groups 

The following example uses NetworkX to compute node degree:

.. doctest::
	
    >>> import netowrkx as nx
	
    >>> G = swn.to_graph()
    >>> node_degree = nx.degree(G)

Upstream, downstream, and travel time metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Since stormwater and wastewater systems typically operate in a unidirectional mode (flow in one direction), 
it is possible to identify assets that are upstream and downstream from other assets.  This calculation helps identify 
travel time along flow paths and capacity limitations along those paths.

Graphics
---------------

Network attributes, simulation results, and resilience metrics can be plotted in several 
ways to better understand system characteristics.  

* Basic network graphics can be generated using the function :class:`~wntr.stormwater.graphics.plot_network`.  
* Time series graphics can be generated using options available in Matplotlib and pandas.
* Fragility curves can be plotted using the function :class:`~wntr.stormwater.graphics.plot_fragility_curve`.  

See drinking water documentation on :ref:`graphics` for more information on graphics capabilities in WNTR.

The following example creates a network plot with invert elevation.

.. doctest::
    :hide:
    
    >>> fig = plt.figure()
    
.. doctest::

    >>> import wntr # doctest: +SKIP
	
    >>> ax = swntr.graphics.plot_network(swn, node_attribute='InvertElev', 
    ...    node_colorbar_label='Invert Elevation')

.. doctest::
    :hide:

    >>> plt.tight_layout()
    >>> plt.savefig('plot_basic_stormwater_network.png', dpi=300)
    
.. _fig-network-2:
.. figure:: figures/plot_basic_stormwater_network.png
   :width: 640
   :alt: Network
   
   Basic stormwater network graphic.


.. _stormwater_examples:

Examples
---------

Travel time between assets
^^^^^^^^^^^^^^^^^^^^^^^^^^

Conduit criticality
^^^^^^^^^^^^^^^^^^^^^

Power outages
^^^^^^^^^^^^^

