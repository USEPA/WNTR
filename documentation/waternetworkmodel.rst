Water network model
======================================

The water network model includes the 
nodes and links in the pipe network, 
demand patterns, 
pump curves,
controls, 
simulation options,
and node coordinates.
This is similar to the model components stored in an EPANET inp file.
Some EPANET [Rossman2000]_ features are not supported by WNTR, as described below.
WNTR also includes features that are not supported by EPANET, 
including leaks, pressure-driven hydraulic simulation, and 
more flexible controls.

A water network model can be created by adding network components to the model::

	wn = wntr.network.WaterNetworkModel()
	wn.add_junction('node1', base_demand=0.01, elevation=100.0, coordinates=(1,2))
	...

A water network model can also be created directly from an EPANET inp file.
EPANET features not supported by WNTR will be printed to the screen::
	
	wn = wntr.network.WaterNetworkModel('Net3.inp')
	
The water network model can be written to a file in EPANET inp file format.
Files are written in LPS units.  
The inp file will not include features not supported by EPANET::

	wn.write_inpfile('filename.inp')
	
The demands associated with pressure-driven simulation can be stored as
demands in the inp file (**NOT COMPLETE**).  See :ref:`simulation_results` for more information on data stored in ``results.node``::

	wn.write_inpfile('filename.inp', results.node['demand'])

The following table describes water network model components.  
EPANET components that are not supported by WNTR are noted.
For more information on the water network model, see the 
:doc:`WaterNetworkModel</apidoc/wntr.network.WaterNetworkModel>` 
module documentation.

==============================  ================================================================================================================================================
Component			Description
==============================  ================================================================================================================================================
Junctions			Junctions are nodes where links connect. 
				Water can enter or leave the network at a junction.
				Junction attributes include the junction name, base demand, elevation, and demand pattern name.
				The method :doc:`add_junction</apidoc/wntr.network.WaterNetworkModel>` can be used add a junction to the network.
				Junctions can also be added using the [JUNCTIONS] section of an EPANET inp file.
				
Reservoirs			Reservoirs are nodes with an infinite external source or sink.
				Reservoirs attributes include reservoir name, base head, and head pattern name.
				The method :doc:`add_reservoir</apidoc/wntr.network.WaterNetworkModel>` can be used add a reservoir to the network.
				Reservoirs can also be added using the [RESERVOIRS] section of an EPANET inp file.
				
Tanks				Tanks are nodes with storage capacity. 
				Tanks attributes include tank name, elevation, initial level, minimum level, maximum level, 
				diameter, minimum volume, and volume curve.
				The method :doc:`add_tank</apidoc/wntr.network.WaterNetworkModel>` can be used add a tank to the network.
				Tanks can also be added using the [TANKS] section of an EPANET inp file.
				**WNTR does not support non-cylindrical shape tanks.**

Emitters			Emitters are nodes with pressure-dependent demand.  Emitters are used for devices such as sprinklers where the flow is 
				not controlled by a customer the way a sink or bathtub faucet is. 
				**WNTR does not support emitters in the [EMMITER] section of an EPANET inp file.  Pressure-driven simulation can be used to simulate emitters.**
				
Pipes				Pipes are links that transport water.
				Pipe attributes include pipe name, start node name, end node name, length, diameter, roughness, 
				minor loss, and status.
				The method :doc:`add_pipe</apidoc/wntr.network.WaterNetworkModel>` can be used add a pipe to the network.
				Pipes can also be added using the [PIPES] section of an EPANET inp file.
				
Pumps				Pumps are links that increase hydraulic head.
				Pump attributes include pump name, start node name, end node name, type, and value.
				The method :doc:`add_pump</apidoc/wntr.network.WaterNetworkModel>` can be used add a pump to the network.
				Pumps can also be added using the [PUMPS] section of an EPANET inp file.
				
Valves				Valves are links that limit pressure or flow.
				Valve attributes include  valve name, start node name, end node name, diameter, type, minor loss, and setting.
				The method :doc:`add_valve</apidoc/wntr.network.WaterNetworkModel>` can be used add a valve to the network.
				Valves can also be added using the [VALVES] section of an EPANET inp file.
				WNTR supports check valves (CV) and pressure-reducing valves (PRV).  
				**WNTR does not support pressure sustaining valves (PSV), 
				pressure breaker valves (PBV),
				flow control valves (FCV),
				throttle control valves (TCV), and 
				general purpose valve (GPV).**

Curves				Curves contain data pairs representing a relationship between two quantities. 
				Curve attributes include curve name, type, and data points. 
				The method :doc:`add_curve</apidoc/wntr.network.WaterNetworkModel>` can be used add a curve to the network.
				Curves can also be added using the [CURVES] section of an EPANET inp file.
				Curves are used to define pump curves.  WNTR supports single point pump curves.
				**WNTR does not support efficiency curves, shape curves, or head loss curves.**

Patterns			Patterns contain data points representing ...
				The method :doc:`add_pattern</apidoc/wntr.network.WaterNetworkModel>` can be used add a pattern to the network.
				Patterns can also be added using the [PATTERNS] section of an EPANET inp file.
				
Time controls			Time controls contain ...
				The method :doc:`add_time_control</apidoc/wntr.network.WaterNetworkModel>` can be used add a time control to the network.
				Time controls can also be added using the [RULES] section of an EPANET inp file.
				
Conditional controls		Conditional controls contain ...
				The method :doc:`add_conditional_control</apidoc/wntr.network.WaterNetworkModel>` can be used add a conditional control to the network.
				Conditional controls can also be added using the [CONTROLS] section of an EPANET inp file.
				
Energy				**WNTR does not support the energy report options in the [ENERGY] section of an EPANET inp file.**

Water quality			**WNTR does not support the water quality options, this includes the [QUALITY], [SOURCES], and [REACTIONS] sections of an EPANET inp file**

Options				[OPTIONS] section of the EPANET inp file.
				[TIME] section of the EPANET inp file.

Coordinates			Coordinates are the x,y location of each node.  WNTR stores node coordinates in a NetworkX graph.
				The method :doc:`set_node_coordinate</apidoc/wntr.network.WaterNetworkModel>` can be used set a node coordinate.
				Node coordinates can be added using the [COORDINATES] section of an EPANET inp file.
==============================  ================================================================================================================================================
