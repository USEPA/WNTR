.. raw:: latex

    \clearpage

Water network model
======================================

The water network model includes 
junctions, tanks, reservoirs, pipes, pumps, valves, 
demand patterns, 
pump curves,
controls, 
sources,
simulation options,
and node coordinates.
Water network models can be built from scratch or built directly from an EPANET INP file.
Sections of EPANET INP file that are not compatible with WNTR are described in :ref:`limitations`.  
The example **water_network_model.py** can be used to generate, save, and modify water network models.

A water network model can be created by adding components to an empty model.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 4-18

A water network model can also be created directly from an EPANET INP file.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 28
   
The water network model can be written to a file in EPANET INP format.
By default, files are written in LPS units.  
The EPANET INP file will not include features not supported by EPANET (i.e., pressure-driven simulation options).

.. literalinclude:: ../examples/water_network_model.py
   :lines: 25

For more information on the water network model, see 
:class:`~wntr.network.model.WaterNetworkModel` in the API documentation.
