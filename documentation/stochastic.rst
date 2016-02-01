Stochastic simulation
======================

Stochastic simulation can be used to evaluate an ensemble of hydraulic and/or water quality 
scenarios.  The location, duration, and severity of different types of disaster events
can be drawn from a distribution and included in the simulation.  Probabilities can 
associated with component failure and restoration.  These probabilities can be
a function of the component (i.e. pipe type or diameter) or supplied by third-party analysis.
Numpy includes many distributions and random selection methods that can be used for stochastic
simulation.  For example, the following code can be used to select N unique pipes 
based on the failure probability of each pipe::
	
	N = 2
	failure_probability = {'pipe1': 0.10, 'pipe2': 0.20, 'pipe3': 0.25, 'pipe4': 0.15, 'pipe5': 0.30}
	pipes_to_fail = np.random.choice(failure_probability.keys(), N, replace=False, p=failure_probability.values())
				     
Likewise, the number of pipes to fail and the start and end time of the failure can be drawn from distributions.  
These selections can be used within loop to run an ensemble of simulations.

WNTR includes several case study examples that demonstrate stochastic simulation
and analysis.  The example **stochastic_simulation.py** runs multiple realizations 
of a power outage and creates graphics of the results.
