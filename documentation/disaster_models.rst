Disaster scenarios
======================================

There are many different disaster scenarios that utility companies may be interested 
in examining. They could be acute like power outages and earthquakes 
or they could examine long term issues like the effect of persistent pipe 
leaks, population increase, and climate change. The following section describes
disaster scenarios that can be modeled in WNTR.  
The example **disaster_scenarios.py** demonstrates methods to define disaster scenarios.

Earthquake
-----------
Earthquakes can be some of the most sudden and impactful disasters that a 
water network experiences. An earthquake can cause lasting damage to the network that 
could take weeks, if not months to fully repair. Earthquakes can cause 
damage to pipes, tanks, and pumps.  
Additionally, earthquakes can cause power outages and fires. WNTR includes methods 
to add leaks to pipes and tanks, 
shut off power to pumps, 
and change demand for fire conditions, as described in the sections below.
The :doc:`Earthquake</apidoc/wntr.scenario.Earthquake>` class includes methods 
to compute PGA, PGV, and repair rate based on the earthquake
location and magnitude.  Since the properties are a function of distance to the epicenter, the 
node coordinates must be scaled properly in units of meters.  
To change the node coordinate scale by a factor of 1000, for example, use the following code:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 9

The following code can be used to compute PGA, PGV, and repair rate:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 10-17

Fragility curves are commonly used to define the probability that a component is 
damaged with respect to 
peak ground acceleration (PGA), 
peak ground velocity (PGV), 
or repair rate.
The American Lifelines Alliance report [ALA2001]_ includes seismic fragility curves 
for water system components.
See :ref:`stochastic_simulation` for more information on fragility curves.

Pipe leaks
-----------
Pipes are susceptible to leaks.  
Ageing infrastructure is susceptible to damage from causes like 
freezing, increased demand, or pressure change. 
This type of damage is especially common in older cities where distribution 
networks were constructed from outdated materials like 
cast iron and even wood. 

To add a leak to a specific pipe:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 25-27

The method ``add_leak`` adds time controls to node to start and stop a leak.

Power outage
-------------
Power outages can be small and brief but can also span over several days and 
effect whole regions as seen in the 2003 Northeast Blackout. 
While the Northeast Blackout was an extreme case, a 2012 LBNL study [Eto2012]_ 
showed the frequency and duration of power outages are increasing by a 
rate of two percent annually. In water distribution networks, 
a power outage can cause pump stations to shut down and result in 
reduced water pressure. This can lead to shortages in some areas of 
the network. There is typically no lasting damage on the network.

To model the impact of a power outage on a specific pump:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 30
   
The method ``add_pump_outage`` adds time controls to a pump to start and stop a power outage.
When simulating power outages, consider placing check bypasses around pumps 
and check valves next to reservoirs.

Fire conditions
----------------
To fight fires, additional water is drawn from the system.  Fire codes vary by 
state.  Minimum required fire flow and duration are generally based on building area and purpose.
While small residential fires may require 1500 gallons/minute for 2 hours, large commercial
spaces may require 8000 gallons/minute for 4 hours.  This additional demand can 
have a large impact on water pressure in the network.

To model the impact of fire conditions at a specific node:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 33-43

Climate change
---------------
Climate change is a long term problem for water distribution 
networks. This problem could lead to 
reduced water availability, 
damage from weather events, 
or even damage from soil movement. 
For example, severe drought in California has forced lawmakers to reduce the 
states water usage by 25 percent. 
Climate change also leads to sea level rise which can inundate distribution 
networks. This is especially prevalent in cities built on unstable soils like 
New Orleans and Washington DC which are experiencing land subsidence. 

To model changes in supply and demand:

.. literalinclude:: ../examples/disaster_scenarios.py
   :lines: 46-49
   
Contamination
--------------------
Water distribution networks are vulnerable to accidental and intentional contamination.
Contamination can enter the system through reservoirs, tanks, and at other access points within the 
distribution network.  Contamination can be difficult to detect and is very expensive to clean up. 
Recent events, including the Elk River chemical spill and Flint lead contamination 
highlight the need minimize human health and economic impacts.

The example **water_quality_simulation.py** includes steps to define and simulate contamination scenarios.
