Water network model
======================================

The water network model includes 
nodes and links in the pipe network, 
demand patterns, 
pump curves,
controls, 
simulation options,
and node coordinates.
Water network models can be built from scratch or built directly from an EPANET INP file.
:numref:`table-framework` lists sections of EPANET INP file that are compatible with WNTR.
The example **water_network_model.py** can be used to generate, save, and modify water network models.

A water network model can be created by adding components to an empty model.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 4-18

A water network model can also be created directly from an EPANET INP file.
EPANET features not supported by WNTR are printed to the screen.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 28
   
The water network model can be written to a file in EPANET format.
By default, files are written in LPS units.  
The inp file will not include features not supported by EPANET.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 25
	
.. 
	Demands associated with pressure-driven simulation can be stored as
	demands in the inp file (**NOT COMPLETE**).  See :ref:`simulation_results` for more information on data stored in ``results.node``.

For more information on the water network model, see the 
:meth:`~wntr.network.model.WaterNetworkModel` documentation.
