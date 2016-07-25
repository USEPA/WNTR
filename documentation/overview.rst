Overview (*DRAFT*)
======================================

Water distribution systems face multiple challenges, including 
aging infrastructure, 
water quality concerns, 
pipe breaks, 
uncertainty in supply and demand, 
natural disasters, 
environmental emergencies, 
and terrorist attacks.  
All of these have the potential to disrupt a large portion of a water system.  
Increasing resilience to these types of hazards is essential to improving 
water security.  Water utilities need to be able to predict how their system 
will perform during disruptive events and understand how to best absorb, 
recover from, and more successfully adapt.  Simulation and analysis tools 
can help water utilities explore how their network will respond to expected, 
and unexpected, events and help inform decisions to make networks
more resilient over time [USEPA2014]_.

The Water Network Tool for Resilience (WNTR, pronounced *winter*) is a python 
package designed to simulate and analyze resilience of 
water distribution networks.  
The API is flexible and allows for changes to the network structure and operations, 
along with simulation of disruptive events and recovery actions.  
The software includes capability to:

.. sidebar:: Example graphics

   .. figure:: figures/overview.png
	   :scale: 100 %
	   :alt: Example graphics
   
* Generate water network models 

  * Compatible with EPANET inp files
  
* Modify network structure

  * Add/remove nodes and links
  * Modify node and link characteristics

* Modify network operation

  * Change initial conditions
  * Change tank, pump, and valve settings
  * Add/remove time-based and conditional controls
  * Add controls based on node and link attributes
  
* Add disruptive events

  * Pipe leak
  * Power outage
  * Contaminant injection
  * Changes to supply and demand

* Add response/repair strategies

  * Fix leaks
  * Restore power
  * Add backup generation
  
* Simulate network hydraulics and water quality

  * Pressure-driven or demand-driven hydraulic equations
  * Track concentration, water age, or percent tracer
  * Pause hydraulic simulations, update network operations, and then restart
  * Run simulations in parallel
  
* Run probabilistic simulations

  * Define fragility curves for component failure
  * Run Monte Carlo simulations
  
* Compute resilience 

  * Topographic, hydraulic metrics, water quality/security, and economic metrics

* Analyze results and generate graphics

  * State transition plots
  * Network graphics and animation


..
	Additional Features (**NOT COMPLETE**)
	* Loss of access (event)
	* Cascading failure (event)
	* Detect contaminant (response/repair strategy)
