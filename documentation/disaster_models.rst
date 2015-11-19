Disaster scenarios
======================================

There are many different disaster scenarios that utility companies may be interested 
in examining. They could be acute disasters like power outages and earthquakes 
or they could examine more long term issues like the effect of persistent pipe 
leaks, population increase, and climate change. The following section reviews 
disaster models in WNTR.

Power outage
-------------
Power outages can be small and brief but can also span over several days and 
effect whole regions as seen in the 2003 Northeast Blackout. While the Northeast 
Blackout was an extreme case, a 2012 LBNL study [Eto2012]_ showed the frequency 
and duration of power outages are increasing by a rate of two percent annually. 
In water distribution networks, a power outage can cause pump stations to shut 
down and result in reduced water pressure. This can lead to shortages in some 
areas of the network. There is typically no lasting damage on the network.

To model a power outage in WNTR...


* When simulating power outages, consider placing check bypasses around pumps.
* When simulating power outages, consider placing check valves next to reservoirs.

Pipe leaks
-----------

To model a pipe leaks in WNTR...

* Pipes with large diameters, large roughness coefficients, and small lengths will have small resistance coefficients. If the resistance coefficient is too small, weird things may happen.


Earthquake
-----------
Earthquakes can be some of the most sudden and impactful disasters that a 
water network can experience. They can cause lasting damage to the network that 
could take weeks, if not months to fully repair. Earthquakes typically effect 
the system by breaking pipes. There are currently multiple modeling techniques 
for predicting pipe breakage due to earthquake damage.

PGA = 0.001 g (~0.01 m/s2): perceptible by people
PGA = 0.02  g (~0.2  m/s2): people lose their balance
PGA = 0.50  g (~5 m/s2): very high; well-designed buildings can survive if the duration is short
https://en.wikipedia.org/wiki/Peak_ground_acceleration
        
Shallow earthquakes are between 0 and 70 km deep, 
intermediate earthquakes, 70 - 300 km deep, 
and deep earthquakes, 300 - 700 km deep
http://earthquake.usgs.gov/learn/topics/seismology/determining_depth.php

Repair rate of 1/km (0.001/m) has been suggested as an upper bound


To model an earthquake in WNTR...
See scenario class :doc:`Earthquake</apidoc/wntr.scenario.Earthquake>`.

Climate change
---------------
Climate change is one of the slower, long term problems for water distribution 
networks. This problem could lead to reduced water availability for a water 
network, damage from weather events, or even damage from soil movement. For 
example, severe drought in California has forced lawmakers to reduce the 
states water usage by 25 percent. The actual reduction amounts vary throughout 
the state with some urban areas are experiencing reductions of 36 percent. 
Climate change is also leading to sea rise which can inundate distribution 
networks. This is especially prevalent in cities built on unstable soils like 
New Orleans and Washington DC which are experiencing land subsidence. There are 
many mechanisms of network failure that can be caused by climate change, 
however, modeling techniques are a fairly recent subject of research.

To model a climate change in WNTR...

Water contamination
--------------------

To model a water contamination in WNTR...
See scenario class :doc:`Waterquality</apidoc/wntr.scenario.Waterquality>`.
