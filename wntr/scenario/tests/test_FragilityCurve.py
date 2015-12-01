from nose.tools import *
from os.path import abspath, dirname, join
import numpy as np
import pandas as pd
from scipy.stats import norm, lognorm
import wntr

testdir = dirname(abspath(str(__file__)))
datadir = join(testdir,'..','..','tests','networks_for_testing')
packdir = join(testdir,'..','..','..')

FC1 = wntr.scenario.FragilityCurve()
FC1.add_state('Major', 2, {'Default': norm(loc=1, scale=2)})
FC1.add_state('Minor', 1, {'Default': norm(loc=0, scale=1)})     

FC2 = wntr.scenario.FragilityCurve()
FC2.add_state('Minor', 1, {'Default': lognorm(0.25, loc=0, scale=1),
                           '3': lognorm(0.2, loc=0, scale=1)})  
FC2.add_state('Major', 2, {'Default': lognorm(0.25, loc=1, scale=2)}) 

#x = np.linspace(-5,5,100)
#for name, state in FC2.states():
#    dist=state.distribution['Default']
#    plt.plot(x,dist.cdf(x), label=name)
#plt.ylim((0,1))
#plt.legend()
    
def test_get_priority_map():
    priority_map = FC1.get_priority_map()
    assert_dict_equal(priority_map, {None: 0, 'Minor': 1, 'Major': 2})

def test_cdf_probability():
    x = pd.Series({'1': 0, '2': 1, '3': 2})
    Pr = FC1.cdf_probability(x)
    assert_equal(Pr.loc['1','Minor'], 0.5)
    assert_less(Pr.loc['2','Minor']-0.841, 0.001)
    assert_less(Pr.loc['3','Minor']-0.977, 0.001)
    assert_equal(Pr.loc['2','Major'], 0.5)

def test_sample_damage_state():
    x = pd.Series({'1': 0, '2': 1, '3': 2})
    Pr = FC1.cdf_probability(x)
    np.random.seed(45)
    states = FC1.sample_damage_state(Pr)
    #p with random seed of 45
    #1    0.989012
    #2    0.549545
    #3    0.281447
    assert_equal(states.loc['1'], None)
    assert_equal(states.loc['2'], 'Minor')
    assert_equal(states.loc['3'], 'Major')

if __name__ == '__main__':
    test_sample_damage_state()
