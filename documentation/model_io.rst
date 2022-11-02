.. raw:: latex

    \clearpage

.. doctest::
    :hide:
	
    >>> import wntr
    >>> try:
    ...    import geopandas as gpd
    ... except ModuleNotFoundError:
    ...    gpd = None
	
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')

.. _model_io:

Model I/O
======================================

The following section describes data and file formats that can used for 
:class:`~wntr.network.model.WaterNetworkModel` input and output (I/O).

EPANET INP file
---------------------------------

The :class:`~wntr.network.io.read_inpfile` function builds a WaterNetworkModel from an EPANET INP file.
The EPANET INP file can be in EPANET 2.00.12 or 2.2.0 format.
The function can also be used to append information from an EPANET INP file into an existing WaterNetworkModel.

.. doctest::

    >>> import wntr
	
    >>> wn = wntr.network.read_inpfile('networks/Net3.inp') # doctest: +SKIP

.. note:: 
   The WaterNetworkModel can also be created from an EPANET INP file as shown below.  
   This is equivalent to using the :class:`~wntr.network.io.read_inpfile` function.
   
   .. doctest::
       
	   >>> wn = wntr.network.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP

The :class:`~wntr.network.io.write_inpfile` function creates an EPANET INP file from a WaterNetworkModel.
By default, files are written in the LPS (liter per second) EPANET unit convention.
The EPANET INP file will not include features not supported by EPANET (i.e., custom element attributes).
EPANET INP files can be saved in EPANET 2.00.12 or 2.2.0 format.

.. doctest::

    >>> wntr.network.write_inpfile(wn, 'filename.inp', version=2.2)
	
Dictionary representation
-------------------------

The :class:`~wntr.network.io.to_dict` function 
creates a dictionary from a WaterNetworkModel.
The dictionary contains the following keys:
 
* nodes (which contains junctions, tanks, and reservoirs)
* links (which contains pipes, pumps, and valves)
* patterns
* curves
* sources
* controls
* options

Each of these entries contains a dictionary or list of dictionaries with keys 
corresponding to object attributes.

.. doctest::

    >>> wn_dict = wntr.network.to_dict(wn)

The :class:`~wntr.network.io.from_dict` function is used to 
create a WaterNetworkModel from a dictionary.
Dictionary representations of the model are always written in SI units (m, kg, s).
The function can also be used to append information from a dictionary into an existing WaterNetworkModel.

.. doctest::

    >>> wn2 = wntr.network.from_dict(wn_dict)

.. note:: 
   :class:`~wntr.network.model.WaterNetworkModel.to_dict` and  
   :class:`~wntr.network.model.WaterNetworkModel.from_dict` 
   are also methods on the WaterNetworkModel.  
   
GeoDataFrame representation
-----------------------------

The :class:`~wntr.network.io.to_gis` function is used to 
create a collection of GeoDataFrames from a WaterNetworkModel.
The collection of GeoDataFrames is stored in a :class:`~wntr.gis.network.WaterNetworkGIS` object 
which contains a GeoDataFrame
for each of the following model components: 

* junctions
* tanks
* reservoirs
* pipes
* pumps
* valves

Note that patterns, curves, sources, controls, and options are not stored in the GeoDataFrame representation.
See :ref:`geospatial` for more information on the use of GeoDataFrames in WNTR. 

.. doctest::
    :skipif: gpd is None

    >>> wn_gis = wntr.network.to_gis(wn)

The :class:`~wntr.network.io.from_gis` function is used to 
create a WaterNetworkModel object from a collection of GeoDataFrames.  
The GeoDataFrames can either be stored in a :class:`~wntr.gis.network.WaterNetworkGIS` object
or in a dictionary with keys for each model component (junctions, tanks, reservoirs, pipes, pumps, and valves).
The function can also be used to append information from GeoDataFrames into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None

    >>> wn2 = wntr.network.from_gis(wn_gis)

A WaterNetworkModel created from GeoDataFrames only contains 
junction, tank, reservoir, pipe, pump and valve
attributes and topographic connectivity of the network.  
The network will **NOT** contain patterns, curves, rules, controls, 
or sources.  Water network model options are set to default values. 
Additional functionality could be added to WNTR in a future release.
   
.. note:: 
   :class:`~wntr.network.model.WaterNetworkModel.to_gis` and  
   :class:`~wntr.network.model.WaterNetworkModel.from_gis` 
   are also methods on the WaterNetworkModel.  

A WaterNetworkGIS object can also be written to GeoJSON and Shapefile files using 
the object's :class:`~wntr.gis.network.WaterNetworkGIS.write` method. 

.. doctest::
    :skipif: gpd is None

    >>> wn_gis.write('Net3', driver='GeoJSON')

Note, the GeoPandas ``read_file`` and ``to_file`` methods can also be used to read and write GeoJSON and Shapefile files.

Graph representation
---------------------

The :class:`~wntr.network.model.WaterNetworkModel.get_graph` method is used to 
create a NetworkX graph from a WaterNetworkModel.
See :ref:`networkx_graph` for more information on the use of NetworkX graphs in WNTR.  

.. doctest::

    >>> G = wn.get_graph()  
	
The ability to create a WaterNetworkModel from 
a NetworkX graph could be added in a future version of WNTR.

JSON file
---------------------------------------------------------

The :class:`~wntr.network.io.write_json` function writes a 
JSON (JavaScript Object Notation) file from a WaterNetworkModel.
The JSON file is a formatted version of the dictionary representation.

.. doctest::

    >>> wntr.network.write_json(wn, 'Net3.json')

The :class:`~wntr.network.io.read_json` function creates a WaterNetworkModel from a 
JSON file.
The function can also be used to append information from a JSON file into an existing WaterNetworkModel.

.. doctest::

    >>> wn2 = wntr.network.read_json('Net3.json')
	
Note that these methods do not check for a valid dictionary/JSON schema prior to building a model.
They simply ignore extraneous or invalid dictionary keys.

GeoJSON files
-------------

The :class:`~wntr.network.io.write_geojson` function writes a collection of 
GeoJSON files from a WaterNetworkModel. 
The GeoJSON files can be loaded into GIS platforms for further analysis and visualization.

.. doctest::
    :skipif: gpd is None
	
    >>> wntr.network.write_geojson(wn, 'Net3')

This creates one file for each of model component (junctions, tanks, reservoirs, pipes, pumps, and valves).
Note that patterns, curves, sources, controls, and options are not stored in the GeoJSON files.

The :class:`~wntr.network.io.read_geojson` function creates a WaterNetworkModel from a 
collection of GeoJSON files.
The function can also be used to append information from GeoJSON files into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None
	
    >>> geojson_files = {'junctions': 'Net3_junctions.geojson',
    ...                  'tanks': 'Net3_tanks.geojson',
    ...                  'reservoirs': 'Net3_reservoirs.geojson',
    ...                  'pipes': 'Net3_pipes.geojson',
    ...                  'pumps': 'Net3_pumps.geojson'}
    >>> wn2 = wntr.network.read_geojson(geojson_files)

Shapefile files
-------------------

The :class:`~wntr.network.io.write_shapefile` function creates 
Shapefile files from a WaterNetworkModel. 
The Shapefiles can be loaded into GIS platforms for further analysis and visualization.

.. doctest::
    :skipif: gpd is None
	
    >>> wntr.network.write_shapefile(wn, 'Net3')
	
This creates a directory for each model component (junctions, tanks, reservoirs, pipes, pumps, and valves)
which contains a Shapefile and related files.
Note that patterns, curves, sources, controls, and options are not stored in the Shapefile files.

The :class:`~wntr.network.io.read_shapefile` function creates a WaterNetworkModel from a collection of
Shapefile directories.
The function can also be used to append information from Shapefiles into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None

    >>> shapefile_dirs = {'junctions': 'Net3_junctions',
    ...                   'tanks': 'Net3_tanks',
    ...                   'reservoirs': 'Net3_reservoirs',
    ...                   'pipes': 'Net3_pipes',
    ...                   'pumps': 'Net3_pumps'}
    >>> wn2 = wntr.network.read_shapefile(shapefile_dirs)
