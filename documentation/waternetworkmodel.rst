Water network model
======================================

The water network model includes 
nodes and links in the pipe network, 
demand patterns, 
pump curves,
controls, 
simulation options,
and node coordinates.
This is similar to the model components stored in an EPANET inp file [Rossman2000]_.
Some EPANET features are not supported by WNTR, 
including non-cylindrical tanks, emitters, and energy reports.
WNTR also includes features that are not supported by EPANET, 
including leaks, pressure-driven hydraulic simulation, and 
more flexible controls.  
The example **water_network_model.py** can be used to generate, save, and modify water network models.

A water network model can be created by adding components to an empty model.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 4-18

A water network model can also be created directly from an EPANET inp file.
EPANET features not supported by WNTR are printed to the screen.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 28
   
The water network model can be written to a file in EPANET inp file format.
By default, files are written in LPS units.  
The inp file will not include features not supported by EPANET.

.. literalinclude:: ../examples/water_network_model.py
   :lines: 25
	
.. 
	Demands associated with pressure-driven simulation can be stored as
	demands in the inp file (**NOT COMPLETE**).  See :ref:`simulation_results` for more information on data stored in ``results.node``.

The following table describes water network model components.  
EPANET components that are not supported by WNTR are noted.
For more information on the water network model, see the 
:doc:`WaterNetworkModel</apidoc/wntr.network.WaterNetworkModel>` 
module documentation.

==============================  ====================================================================================================================================================
Component			Description
==============================  ====================================================================================================================================================
Junctions			Junctions are nodes where links connect. 
				Water can enter or leave the network at a junction.
				Junction attributes include the junction name, base demand, elevation, and demand pattern name.
				The method :doc:`add_junction</apidoc/wntr.network.WaterNetworkModel>` can be used to add a junction to the network.
				Junctions can also be added using the [JUNCTIONS] section of an EPANET inp file.
				
Reservoirs			Reservoirs are nodes with an infinite external source or sink.
				Reservoir attributes include reservoir name, base head, and head pattern name.
				The method :doc:`add_reservoir</apidoc/wntr.network.WaterNetworkModel>` can be used to add a reservoir to the network.
				Reservoirs can also be added using the [RESERVOIRS] section of an EPANET inp file.
				
Tanks				Tanks are nodes with storage capacity. 
				Tank attributes include tank name, elevation, initial level, minimum level, maximum level, 
				diameter, minimum volume, and volume curve.
				The method :doc:`add_tank</apidoc/wntr.network.WaterNetworkModel>` can be used to add a tank to the network.
				Tanks can also be added using the [TANKS] section of an EPANET inp file.
				**WNTR does not support non-cylindrical shape tanks.**

Emitters			Emitters are nodes with pressure-dependent demand.  Emitters are used for devices such as sprinklers where the flow is 
				not controlled by a customer the way a sink or bathtub faucet is. 
				**WNTR does not support emitters in the [EMMITER] section of an EPANET inp file.  Pressure-driven simulation can be used to simulate emitters.**
				
Pipes				Pipes are links that transport water.
				Pipe attributes include pipe name, start node name, end node name, length, diameter, roughness, 
				minor loss, and status.
				The method :doc:`add_pipe</apidoc/wntr.network.WaterNetworkModel>` can be used to add a pipe to the network.
				Pipes can also be added using the [PIPES] section of an EPANET inp file.
				
Pumps				Pumps are links that increase hydraulic head.
				Pump attributes include pump name, start node name, end node name, type, and value.
				The method :doc:`add_pump</apidoc/wntr.network.WaterNetworkModel>` can be used to add a pump to the network.
				Pumps can also be added using the [PUMPS] section of an EPANET inp file.
				
Valves				Valves are links that limit pressure or flow.
				Valve attributes include valve name, start node name, end node name, diameter, type, minor loss, and setting.
				The method :doc:`add_valve</apidoc/wntr.network.WaterNetworkModel>` can be used to add a valve to the network.
				Valves can also be added using the [VALVES] section of an EPANET inp file.
				WNTR supports check valves (CV) and pressure-reducing valves (PRV).  
				**WNTR does not support pressure sustaining valves (PSV), 
				pressure breaker valves (PBV),
				flow control valves (FCV),
				throttle control valves (TCV), and 
				general purpose valve (GPV).**

Curves				Curves contain data pairs representing a relationship between two quantities. 
				Curve attributes include curve name, type, and data points. 
				The method :doc:`add_curve</apidoc/wntr.network.WaterNetworkModel>` can be used to add a curve to the network.
				Curves can also be added using the [CURVES] section of an EPANET inp file.
				Curves are used to define pump curves.  WNTR supports single point pump curves.
				**WNTR does not support efficiency curves, shape curves, or head loss curves.**

Patterns			Patterns contain data points representing a time-series.
				The method :doc:`add_pattern</apidoc/wntr.network.WaterNetworkModel>` can be used to add a pattern to the network.
				Patterns are used to define demand patterns.  
				Patterns can also be added using the [PATTERNS] section of an EPANET inp file.
				
Time controls			Time controls define actions that starts or stops at a particular time.
				The class :doc:`TimeControl</apidoc/wntr.network.NetworkControls>` can be used to add a time control to the network.
				Time controls can also be added using the [RULES] section of an EPANET inp file.
				
Conditional controls		Conditional controls define actions that starts or stops based on a particular condition in the network. 
				The method :doc:`ConditionalControl</apidoc/wntr.network.NetworkControls>` can be used to add a conditional control to the network.
				Conditional controls can also be added using the [CONTROLS] section of an EPANET inp file.
				
Energy				**WNTR does not support the energy report options in the [ENERGY] section of an EPANET inp file.**

Water quality			The [QUALITY], [SOURCES], and [REACTIONS] options of the EPANET inp file are used when simulating water quality with the EpanetSimulator.

Options				Options are defined in the class :doc:`WaterNetworkOptions</apidoc/wntr.network.WaterNetworkModel>`. 
				These options include input in the [OPTIONS] and [TIME] section of the EPANET inp file.

Coordinates			Coordinates are the x,y location of each node.  WNTR stores node coordinates in a NetworkX graph.
				The method :doc:`set_node_coordinate</apidoc/wntr.network.WaterNetworkModel>` can be used to set a node coordinate.
				Node coordinates can be added using the [COORDINATES] section of an EPANET inp file.
==============================  ====================================================================================================================================================
