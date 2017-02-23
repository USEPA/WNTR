Disaster scenarios
======================================

Drinking water utilities might be interested in examining many different disaster scenarios.
They could be acute incidents like power outages and earthquakes 
or they could be long term issues like persistent pipe 
leaks, population fluctuation, and climate change. The following section describes
disaster scenarios that can be modeled in WNTR.  
The example **disaster_scenarios.py** demonstrates methods to define disaster scenarios.

Earthquake
-----------
Earthquakes can be some of the most sudden and impactful disasters that a 
water network experiences. An earthquake can cause lasting damage to the network that 
could take weeks, if not months, to fully repair. Earthquakes can cause 
damage to pipes, tanks, pumps, and other infrastructure.
Additionally, earthquakes can cause power outages and fires. 

WNTR includes methods 
to add leaks to pipes and tanks, 
shut off power to pumps, 
and change demands for fire conditions, as described in the sections below.
The :meth:`~wntr.scenario.earthquake.Earthquake` class includes methods 
to compute peak ground acceleration, peak ground velocity, and repair rate based on the earthquake
location and magnitude.  
Alternatively, external earthquake models or databases (i.e. ShakeMap [WWQP06]_) can be used to compute earthquake properties and 
those properties can be loaded into Python for analysis in WNTR.

When simulating the effects of an earthquake, fragility curves are commonly used to define the probability that a component is 
damaged with respect to 
peak ground acceleration, peak ground velocity, 
or repair rate.
The American Lifelines Alliance report [ALA01]_ includes seismic fragility curves 
for water system components.
See :ref:`stochastic_simulation` for more information on fragility curves.

Since properties like peak ground acceleration, peak ground velocity, and repair rate are a function of distance to the epicenter, 
node coordinates in the water network model must be in units of meters.  
Since some network models use other units for node coordinates, 
WNTR includes a method to change the coordinate scale.  
To change the node coordinate scale by a factor of 1000, for example, use the following code:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 9
   
The following code can be used to compute peak ground acceleration, peak ground velocity, and repair rate:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 10-17


Pipe leaks
-----------
Pipes are susceptible to leaks.  Leaks can be caused by 
aging infrastructure, 
the freezing/thaw process, 
increased demand, 
or pressure changes. 
This type of damage is especially common in older cities where distribution 
networks were constructed from outdated materials like 
cast iron and even wood. 

WNTR includes methods to add leaks to junctions and tanks.
Leaks can be added to a pipe by splitting the pipe and adding a junction.
To add a leak to a specific pipe:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 25-27

The method :meth:`~wntr.network.model.Junction.add_leak` adds time controls to a junction which includes the start and stop time for the leak.

Power outage
-------------
Power outages can be small and brief, but can also span over several days and 
effect whole regions as seen in the 2003 Northeast Blackout. 
While the Northeast Blackout was an extreme case, a 2012 Lawrence Berkeley National Laboratory study [ELLT12]_ 
showed the frequency and duration of power outages are increasing by a 
rate of two percent annually. In water distribution networks, 
a power outage can cause pump stations to shut down and result in 
reduced water pressure. This can lead to shortages in some areas of 
the network. Typically, no lasting damage in the network is associated with power outages. 

WNTR can be used to simulate power outages by changing the pump status from ON to OFF and defining the duration of the outage.
To model the impact of a power outage on a specific pump:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 30
   
The method :meth:`~wntr.network.model.WaterNetworkModel.add_pump_outage` adds time controls to a pump to start and stop a power outage.
When simulating power outages, consider placing check bypasses around pumps 
and check valves next to reservoirs.

Fire conditions
----------------
To fight fires, additional water is drawn from the network.  Fire codes vary by 
state.  Minimum required fire flow and duration are generally based on building area and purpose.
While small residential fires might require 1500 gallons/minute for 2 hours, large commercial
spaces might require 8000 gallons/minute for 4 hours [ICC12]_.  This additional demand can 
have a large impact on water pressure in the network.  

WNTR can be used to simulate fire fighting conditions in the network.  
WNTR simulates fire fighting conditions by specifying the demand, time, and duration of fire fighting.
Pressure-driven demand simulation is recommended in cases where fire fighting might impact expected demand.
To model the impact of fire conditions at a specific node:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 33-43

Climate change
---------------
Climate change is a long term problem for water distribution 
networks. This problem could lead to 
reduced water availability, 
damage from weather incidents, 
or even damage from subsidence. 
For example, severe drought in California has forced lawmakers to reduce the 
state's water usage by 25 percent. 
Climate change also leads to sea level rise which can inundate distribution 
networks. This is especially prevalent in cities built on unstable soils like 
New Orleans and Washington DC which are experiencing land subsidence. 

WNTR can be used to simulate the effects of climate change on the water distribution network by
changing supply and demand, adding disruptive conditions (i.e. power outages, pipe leaks) caused by severe weather, or by adding pipe leaks caused by subsidence.
Power outages and pipe leaks are discribed above.  
Changes to supply and demand can be simple (i.e. changing all nodes by a certain percent), or complex (i.e. using external data or correlated statistical methods).
To model simple changes in supply and demand:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 46-49
   
Contamination
--------------------
Water distribution networks are vulnerable to accidental and intentional contamination.
Contamination can enter the system through reservoirs, tanks, and at other access points within the 
distribution network.  Contamination can be difficult to detect and is very expensive to clean up. 
Recent incidents, including the Elk River chemical spill and Flint lead contamination, 
highlight the need minimize human health and economic impacts.

WNTR can be used to simulate contamination incidents. 
The :meth:`~wntr.scenario.water_quality.Waterquality` class is used to define the injection location, rate, and start and end times.
The example **water_quality_simulation.py** includes steps to define and simulate contamination incidents.
