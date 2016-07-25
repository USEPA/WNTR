import pandas as pd
import numpy as np

class FragilityCurve(object):
    """
   Fragility Curve class.
    """

    def __init__(self):
        self._num_states = 0
        self._states = {}

    def add_state(self, name, priority=0, distribution={}):
        """
        Add a damage state distribution
        
        Parameters
        ----------
        name : string
            Name of the damage state
        
        priority : int
            Damage state priority
        
        distribution : dict, key = string, value = scipy.stats statistical function
            'Default' can be used to specificy all location
        """
        state = State(name, priority, distribution)
        self._states[name] = state
        self._num_states += 1
    
    def states(self):
        """
        A generator to iterate over all states, in order of priority

        Returns
        -------
        state_name, state
        """
        sorted_list = [x for x in self._states.iteritems()] 
        sorted_list.sort(key=lambda x: x[1].priority) 
        
        for state_name, state in sorted_list:
            yield state_name, state
    
    def get_priority_map(self):
        """
        Returns a dictonary of state name and priority number.
        """
        priority_map = {None: 0}
        
        for state_name, state in self.states():
            priority_map[state_name] = state.priority
            
        return priority_map
        
    def cdf_probability(self, x):
        """
        Return the CDF probability for each state, based on the value of x
        
        Parameters
        -----------
        x : pd.Series
            Control variable for each element
            
        Returns
        --------
        Pr : pd.Dataframe
            Probability of exceeding a damage state
        
        """
        state_names = [name for name, state in self.states()]
        
        Pr = pd.DataFrame(index = x.index, columns=state_names)

        for element in Pr.index:
            for state_name, state in self.states():
                try:
                    dist=state.distribution[element]
                except:
                    dist=state.distribution['Default']
                Pr.loc[element, state_name] = dist.cdf(x[element])
            
        return Pr
    
    def sample_damage_state(self, Pr):
        """
        Sample the damage state using a uniform random variable
        
         Parameters
        -----------
        Pr : pd.Dataframe
            Probability of exceeding a damage state
            
        Returns
        -------
        damage_state : pd.Series
            The damage state of each element
        """
        p = pd.Series(data = np.random.uniform(size=Pr.shape[0]), index=Pr.index)
        
        damage_state = pd.Series(data=[None]* Pr.shape[0], index=Pr.index)
        
        for DS_names in Pr.columns:
            damage_state[p < Pr[DS_names]] = DS_names
        
        return damage_state
        
class State(object):

    def __init__(self, name, priority=0.0, distribution={}):
        """
        Parameters
        -----------
        name : string
            Name of the damage state
            
        priority : int
            
        distribution : dict
        """
        self.name = name
        self.priority = priority
        self.distribution = distribution
