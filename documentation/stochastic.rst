.. raw:: latex

    \clearpage

.. _stochastic_simulation:

Stochastic simulation
===============================

Stochastic simulation can be used to evaluate an ensemble of hydraulic and/or water quality 
scenarios.  For disaster scenarios, the location, duration, and severity of different types of incidents
can be drawn from distributions and included in the simulation.  
Distributions can be a function of component properties (i.e., age, material) or 
based on engineering standards.
The Python packages Numpy and Scipy include statistical distributions and random selection methods that can be used for stochastic
simulation.  

For example, the following code can be used to select N unique pipes 
based on the failure probability of each pipe::
	
	N = 2
	failure_probability = {'pipe1': 0.10, 'pipe2': 0.20, 'pipe3': 0.25, 'pipe4': 0.15, 
		'pipe5': 0.30}
	pipes_to_fail = np.random.choice(failure_probability.keys(), N, replace=False, 
		p=failure_probability.values())
				     
The example **stochastic_simulation.py** runs multiple realizations 
of a pipe leak scenario where the location and duration are drawn from probability 
distributions.

Fragility curves
-------------------
Fragility curves are commonly used in disaster models to define the probability 
of exceeding a given damage state as a function environmental change.
Fragility curves are closely related to survival curves, which are used to define the probability of component failure due to age.  
To estimate earthquake damage, fragility curves are defined as a function of peak
ground acceleration, peak ground velocity, or repair rate.  
The American Lifelines Alliance report [ALA01]_
includes seismic fragility curves for water network components.
Fragility curves can also
be defined as a function of flood stage, wind speed, and temperature for other
types of disasters.  

Fragility curves can have multiple damage states.  
Each state should correspond to specific changes to the network model that represent damage, for example, a major or minor leak.
Each state is defined with a name (i.e., 'Major', 'Minor'), 
priority (i.e., 1, 2, where higher numbers = higher priority), 
and distribution (using the Scipy Python package).
The distribution can be defined for all elements using the keyword 'Default', 
or can be defined for individual components.
Each fragility curve includes a "No damage" state with priority 0 (lowest priority).

The example **fragility_curves.py** uses fragility curves to 
determine probability of failure:

.. literalinclude:: ../examples/fragility_curves.py
   :lines: 2, 25-27

:numref:`fig-fragility` illustrates a fragility curve based on peak ground acceleration with
two damage states: Minor damage and Major damage.  For example, if the peak ground acceleration is 0.5 at 
a specific junction, the probability of exceeding a Major damage state 0.25 and the probability
of exceeding the Minor damage state is 0.85.  For each stochastic simulation, a random number is 
drawn between 0 and 1.  If the random number is between 0 and 0.25, the junction is assigned Minor damage.
If the random number is between 0.25 and 0.85, then the junction is assigned Major damage. 
If the random number is between 0.85 and 1, then the junction is assigned No damage.
After selecting a damage state for the junction, the network should be changed to reflect the associated damage.
For example, if the junction has Major damage, a large leak might be defined at that location.

.. _fig-fragility:
.. figure:: figures/fragility_curve.png
   :scale: 100 %
   :alt: Fragility curve

   Example fragility curve.
   

