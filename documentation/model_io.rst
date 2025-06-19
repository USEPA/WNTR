.. raw:: latex

    \clearpage

.. doctest::
    :hide:
	
    >>> import wntr
    >>> import pandas as pd
    >>> try:
    ...    import geopandas as gpd
    ... except ModuleNotFoundError:
    ...    gpd = None
	
.. _model_io:

Model I/O
======================================

The following section describes the data and file formats that can used for the 
:class:`~wntr.network.model.WaterNetworkModel` input and output (I/O).

EPANET INP file
---------------------------------

The :class:`~wntr.network.io.read_inpfile` function builds a WaterNetworkModel from an EPANET INP file.
The EPANET INP file can be in the EPANET 2.00.12 or 2.2.0 format.
See https://epanet22.readthedocs.io for more information on EPANET INP file format.

The function can also be used to append information from an EPANET INP file into an existing WaterNetworkModel.

.. doctest::

    >>> import wntr
	
    >>> wn = wntr.network.read_inpfile('networks/Net3.inp') # doctest: +SKIP

.. note:: 
   The WaterNetworkModel can also be created from an EPANET INP file as shown below.  
   This is equivalent to using the :class:`~wntr.network.io.read_inpfile` function.
   
   .. doctest::
       
	   >>> wn = wntr.network.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP
	   
   EPANET INP files can also be accessed using the model library, see :ref:`model_library` for more details.  
   This allows the user to create a WaterNetworkModel from a model name.
 
   .. doctest::
       
	  >>> wn = wntr.network.WaterNetworkModel('Net3')

The :class:`~wntr.network.io.write_inpfile` function creates an EPANET INP file from a WaterNetworkModel.
By default, files are written in the LPS (liter per second) EPANET unit convention.
The EPANET INP file will not include features not supported by EPANET (i.e., custom element attributes).
EPANET INP files can be saved in the EPANET 2.00.12 or 2.2.0 format.

.. doctest::

    >>> wntr.network.write_inpfile(wn, 'filename.inp', version=2.2)

.. _dictionary_representation:

Dictionary representation
-------------------------

The :class:`~wntr.network.io.to_dict` function 
creates a dictionary, a Python data structure, from a WaterNetworkModel.
The dictionary contains the following keys:
 
* nodes (which contains junctions, tanks, and reservoirs)
* links (which contains pipes, pumps, and valves)
* patterns
* curves
* sources
* controls
* options

Each of these entries contains a dictionary or list of dictionaries with keys 
corresponding to object attributes. A small subset of the dictionary is printed below.

.. doctest::

    >>> wn_dict = wntr.network.to_dict(wn)
    >>> wn_dict['links'][0] # doctest: +SKIP
	{'name': '20', 'link_type': 'Pipe', 'start_node_name': '3', 'end_node_name': '20', ...
	
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
See :ref:`geospatial` for more information on the the :class:`~wntr.gis.network.WaterNetworkGIS` object and the use of GeoDataFrames in WNTR. 

.. doctest::
    :skipif: gpd is None

    >>> wn_gis = wntr.network.to_gis(wn)

Individual GeoDataFrames are obtained as follows (Note that the example network, Net3, has no valves and thus the GeoDataFrame for valves is empty).

.. doctest::
    :skipif: gpd is None

    >>> wn_gis.junctions # doctest: +SKIP
    >>> wn_gis.tanks # doctest: +SKIP
    >>> wn_gis.reservoirs # doctest: +SKIP
    >>> wn_gis.pipes # doctest: +SKIP
    >>> wn_gis.pumps # doctest: +SKIP
    >>> wn_gis.valves # doctest: +SKIP
	
The :class:`~wntr.network.io.from_gis` function is used to 
create a WaterNetworkModel object from a collection of GeoDataFrames.  
The GeoDataFrames can either be stored in a WaterNetworkGIS object
or in a dictionary with keys for each model component (junctions, tanks, reservoirs, pipes, pumps, and valves).
The function can also be used to append information from GeoDataFrames into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None

    >>> wn2 = wntr.network.from_gis(wn_gis)

A WaterNetworkModel created from GeoDataFrames only contains 
the junction, tank, reservoir, pipe, pump, and valve
attributes and topographic connectivity of the network.  
The network will not contain patterns, curves, rules, controls, 
or sources. The water network model options are set to default values. 
Additional functionality could be added to WNTR in a future release.
   
.. note:: 
   :class:`~wntr.network.model.WaterNetworkModel.to_gis` and  
   :class:`~wntr.network.model.WaterNetworkModel.from_gis` 
   are also methods on the WaterNetworkModel.  

Graph representation
---------------------

The :class:`~wntr.network.io.to_graph` method is used to 
create a NetworkX graph from a WaterNetworkModel.
See :ref:`networkx_graph` for more information on the use of NetworkX graphs in WNTR.  

.. doctest::

    >>> G = wntr.network.to_graph(wn)  
	
The ability to create a WaterNetworkModel from 
a NetworkX graph could be added in a future version of WNTR.

.. note:: 
   :class:`~wntr.network.model.WaterNetworkModel.to_graph`
   is also a method on the WaterNetworkModel.  
   
JSON file
---------------------------------------------------------

JSON (JavaScript Object Notation) files store a collection of name/value pairs that is easy to read in text format.
More information on JSON files is available at https://www.json.org.
The format of JSON files in WNTR is based on the :ref:`dictionary_representation` of the WaterNetworkModel.

The :class:`~wntr.network.io.write_json` function writes a 
JSON file from a WaterNetworkModel.
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

GeoJSON files are commonly used to store geographic data structures. 
More information on GeoJSON files can be found at https://geojson.org.

When reading GeoJSON files into WNTR, the file should contain columns from the set of valid column names. 
Valid GeoJSON column names can be obtained using the :class:`~wntr.network.io.valid_gis_names` function. 
By default, the function returns a complete set of required and optional column names. 
A minimal list of column names containing commonly used attributes can be obtained by setting ``complete_list`` to False. 
The minimal set correspond with attributes used in :class:`~wntr.network.model.WaterNetworkModel.add_junction`, :class:`~wntr.network.model.WaterNetworkModel.add_tank`, etc.  
Columns that are optional (i.e., ``initial_quality``) and not included in the GeoJSON file are defined using default values.

The following examples return the complete and minimal lists of valid GeoJSON column names for junctions.

.. doctest::
    :skipif: gpd is None

    >>> geojson_column_names = wntr.network.io.valid_gis_names()
    >>> print(geojson_column_names['junctions'])
    ['name', 'base_demand', 'demand_pattern', 'elevation', 'demand_category', 'geometry', 'emitter_coefficient', 'initial_quality', 'minimum_pressure', 'required_pressure', 'pressure_exponent', 'tag']

.. doctest::
    :skipif: gpd is None

    >>> geojson_column_names = wntr.network.io.valid_gis_names(complete_list=False)
    >>> print(geojson_column_names['junctions'])
    ['name', 'base_demand', 'demand_pattern', 'elevation', 'demand_category', 'geometry']

Note that GeoJSON files can contain additional custom column names that are assigned to WaterNetworkModel objects.

The :class:`~wntr.network.io.write_geojson` function writes a collection of 
GeoJSON files from a WaterNetworkModel. 
The GeoJSON files can be loaded into geographic information
system (GIS) platforms for further analysis and visualization.

.. doctest::
    :skipif: gpd is None
	
    >>> wntr.network.write_geojson(wn, 'Net3')

This creates the following GeoJSON files for junctions, tanks, reservoirs, pipes, and pumps:

* Net3_junctions.geojson
* Net3_tanks.geojson
* Net3_reservoirs.geojson
* Net3_pipes.geojson
* Net3_pumps.geojson

A GeoJSON file for valves, Net3_valves.geojson, is not created since Net3 has no valves. 
Note that patterns, curves, sources, controls, and options are not stored in the GeoJSON files.

The :class:`~wntr.network.io.read_geojson` function creates a WaterNetworkModel from a 
dictionary of GeoJSON files.  
Valid column names and additional custom attributes are added to the model.
The function can also be used to append information from GeoJSON files into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None
	
    >>> geojson_files = {'junctions': 'Net3_junctions.geojson',
    ...                  'tanks': 'Net3_tanks.geojson',
    ...                  'reservoirs': 'Net3_reservoirs.geojson',
    ...                  'pipes': 'Net3_pipes.geojson',
    ...                  'pumps': 'Net3_pumps.geojson'}
    >>> wn2 = wntr.network.read_geojson(geojson_files)

.. note:: 
   :class:`~wntr.gis.network.WaterNetworkGIS.write_geojson` and
   :class:`~wntr.gis.network.WaterNetworkGIS.read_geojson`
   are also methods on the WaterNetworkGIS object. 


.. _shapefile_format:

Shapefile
-------------------

A Shapefile is a collection of vector data storage files used to store geographic data.
The file format is developed and regulated by Esri.
For more information on Shapefiles, see https://www.esri.com.

To use Esri Shapefiles in WNTR, several formatting requirements are enforced:

* Geospatial data containing junction, tank, reservoir, pipe, pump, and valve data 
  are stored in separate Shapefile directories.

* The namespace for Node names (which includes junctions, tanks, and reservoirs) 
  must be unique.  Likewise, the namespace for Links (which includes pipes, 
  pumps, and valves) must be unique.  For example, this means that a junction
  cannot have the same name as a tank.
  
* The Shapefile geometry is in a format compatible with GeoPandas, namely a 
  Point, LineString, or MultiLineString.  See :ref:`gis_data` for 
  more information on geometries.
  
* Shapefiles truncate field names to 10 characters, while WaterNetworkModel 
  node and link attribute names are often longer.  For this reason, it is
  assumed that the first 10 characters of each attribute are unique.  
  
* When reading Shapefiles files into WNTR, the file should contain fields from the set of valid column names.
  Valid Shapefiles field names can be obtained using the 
  :class:`~wntr.network.io.valid_gis_names` function. By default, the function
  returns a complete set of required and optional field names. 
  A minimal list of field names containing commonly used attributes can be obtained by setting ``complete_list`` to False. 
  The minimal set correspond with attributes used in `add_junction`, `add_tank`, etc.  
  Fields that are optional (i.e., ``initial_quality``) and not included in the Shapefile are defined using default values.

  For Shapefiles, the `truncate_names` input parameter should be set to 10 (characters).
  The following examples return the complete and minimal lists of valid Shapefile field names for junctions.
  Note that attributes like ``minimum_pressure`` are truncated to ``minimum_pr``. 

  .. doctest::
      :skipif: gpd is None

      >>> shapefile_field_names = wntr.network.io.valid_gis_names(truncate_names=10)
      >>> print(shapefile_field_names['junctions'])
      ['name', 'base_deman', 'demand_pat', 'elevation', 'demand_cat', 'geometry', 'emitter_co', 'initial_qu', 'minimum_pr', 'required_p', 'pressure_e', 'tag']

  .. doctest::
      :skipif: gpd is None

      >>> shapefile_field_names = wntr.network.io.valid_gis_names(complete_list=False, 
      ...    truncate_names=10)
      >>> print(shapefile_field_names['junctions'])
      ['name', 'base_deman', 'demand_pat', 'elevation', 'demand_cat', 'geometry']
	  
* Shapefiles can contain additional custom field names that are assigned to WaterNetworkModel objects.

  
The :class:`~wntr.network.io.write_shapefile` function creates 
Shapefiles from a WaterNetworkModel. 
The Shapefiles can be loaded into GIS platforms for further analysis and visualization.

.. doctest::
    :skipif: gpd is None
	
    >>> wntr.network.write_shapefile(wn, 'Net3')
	
This creates the following Shapefile directories for junctions, tanks, reservoirs, pipes, and pumps:

* Net3_junctions
* Net3_tanks
* Net3_reservoirs
* Net3_pipes
* Net3_pumps

A Shapefile for valves, Net3_valves, is not created since Net3 has no valves.
Note that patterns, curves, sources, controls, and options are not stored in the Shapefiles.

The :class:`~wntr.network.io.read_shapefile` function creates a WaterNetworkModel from a dictionary of
Shapefile directories.
Valid field names and additional custom field names are added to the model.
The function can also be used to append information from Shapefiles into an existing WaterNetworkModel.

.. doctest::
    :skipif: gpd is None

    >>> shapefile_dirs = {'junctions': 'Net3_junctions',
    ...                   'tanks': 'Net3_tanks',
    ...                   'reservoirs': 'Net3_reservoirs',
    ...                   'pipes': 'Net3_pipes',
    ...                   'pumps': 'Net3_pumps'}
    >>> wn2 = wntr.network.read_shapefile(shapefile_dirs)

.. note:: 
   :class:`~wntr.gis.network.WaterNetworkGIS.write_shapefile` and
   :class:`~wntr.gis.network.WaterNetworkGIS.read_shapefile`
   are also methods on the WaterNetworkGIS object. 
   