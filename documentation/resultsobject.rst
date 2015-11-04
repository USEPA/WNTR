Simulation results
====================
Simulation results are stored in Pandas Panels.  
For more information on Pandas, see http://pandas.pydata.org/.
Results are stored in one Panel for nodes and one Panel for links, accessed using :: 

	results.node
	results.link

Each Panel is indexed by item, major_axis, and minor_axis.

* item
    For node panels: demand, pressure, head, type
    
    For link panels: velocity, flowrate, type
* major_axis
	Time in seconds from the start of the simulation
* minor_axis
	For node panels: Node name
	
	For link panels: Link name

For example, to access the pressure and demand at node '123' at 1 hour, use the following code::

	results.node.loc[['pressure', 'demand'], 3600, '123']
	
To access the pressure for all nodes and times, use the following code::

	results.node.loc['pressure', :, :]

Attributes can be plotted on the water network model using::
	
	pressure_at_1hr = results.node.loc['pressure', 3600, :]
	wntr.network.draw_graph(wn, node_attribute=pressure_at_1hr)

Attributes can be plotted as a time-series using::
	
	pressure_at_node123 = results.node.loc['pressure', :, '123']
	pressure_at_node123.plot()

Panels can be saved to excel files using the following code::

	results.node.to_excel('node_results.xls')
	results.link.to_excel('link_results.xls')
