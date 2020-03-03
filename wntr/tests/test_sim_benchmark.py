# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 17:30:22 2020

@author: dlvilla
"""
import unittest
from os.path import abspath, dirname, join
from nose.tools import *
import wntr
from scipy.optimize import fsolve
from scipy.integrate import solve_ivp

from numpy import pi, arange,squeeze,array, zeros,sqrt, interp, mean
from matplotlib import pyplot as plt

testdir = dirname(abspath(str(__file__)))


class Test_Benchmarks(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        import wntr
        self.wntr = wntr

    @classmethod
    def tearDownClass(self):
        pass

    def test_wntr_vs_ode_solution(self):
        
        h20 = 150.0  # meters
        D = 1.0     # meters
        d = 0.2      # meters
        L = sqrt(2) * h20     # meters
        C = 130      # Pipe friction factor (new cast iron)
        tf = 400.0
        pA = 200.0
        pB = 4.0
        dt_max = 1.0
        dt_max_wntr = [1,10,50,100]
        wn = self.wntr.network.WaterNetworkModel()
        
        # build the equivalent WNTR model
        # add nodes 
        
        wn.add_reservoir("r1",base_head=0.0,coordinates=(0,0))
        wn.add_junction("j1",base_demand=0.0,elevation=0.0,coordinates=(0,0))
        wn.add_tank("t1",elevation=h20,init_level=0.0,min_level=0.0,max_level=1.0e10,
                    diameter=D, min_vol=0.0,coordinates=(h20,0.0))
        # add links
        wn.add_pipe("p1",start_node_name="j1",end_node_name="t1",length=L,diameter=d,
                    roughness=C,minor_loss=0.0)
        wn.add_curve("pump1_curve","HEAD",[(0.0,pA),(pA/pB,0.0)])
        wn.add_pump("pump1",start_node_name="r1",end_node_name="j1",
                    pump_type="HEAD",pump_parameter="pump1_curve",speed=1.0)
        
        wn.options.time.duration=tf
        wn.options.hydraulic.headloss="H-W"
        wn.options.hydraulic.viscosity=0.0
        wn.options.hydraulic.specific_gravity=1.0
        
        # run the wntr model
        sim = self.wntr.sim.WNTRSimulator(wn)
        results = []
        for dtmax in dt_max_wntr:
            wn.options.time.hydraulic_timestep=dtmax
            wn.options.time.report_timestep=dtmax
            result = sim.run_sim()
            results.append(result)
            wn.reset_initial_values()
        
        # run the ode solution
        Q,t,h2 = single_reservoir_pump_pipe_tank_ode_solution(h20,D,d,L,C,tf,pA,pB,dt_max)
        
        create_graph = False
        if create_graph:
            fig,axl = plt.subplots(2,1)
            fig.set_figheight(6)
            fig.set_figwidth(10)
            
            axl[0].set_title("Single pump with 200m maximum head capacity pumping to a tank with initial elevation head of 150m")
            axl[0].plot(t,Q,label="ode",linewidth=3,linestyle="--")
            for dt,result in zip(dt_max_wntr,results):
                axl[0].plot(result.link['flowrate']['p1'],label="wntr dt={0:4.0f}".format(dt))
            axl[0].legend()
            axl[0].grid("on")
            axl[0].set_ylabel('flow rate (m3/s)')
            
            
            axl[1].plot(t,h2,label='ode',linewidth=3,linestyle="--")
            for dt,result in zip(dt_max_wntr,results):
                axl[1].plot(result.node['head']['t1'],label="wntr dt={0:4.0f}".format(dt))
            axl[1].set_xlabel('time (s)')
            axl[1].set_ylabel('tank head (m)')
            axl[1].grid("on")
            plt.savefig(join(testdir,"SinglePumpTankExampleWNTRvsODE.png"),dpi=300)
    
        h_wntr_interp = interp(t,results[0].node['head']['t1'].index,
                               results[0].node['head']['t1'].values)
        hR2 = self._R2(h2,h_wntr_interp)
        self.assertLessEqual(0.95,hR2,msg="The WNTR numerical solution for tank head has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")
        
        Q_wntr_interp = interp(t,results[0].link['flowrate']['pump1'].index,
                               results[0].link['flowrate']['pump1'].values)
        QR2 = self._R2(Q,Q_wntr_interp)
        self.assertLessEqual(0.95,QR2,msg="The WNTR numerical solution for flow rate has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")

    def _R2(self,y,f):
        y_bar = mean(y)
        ss_tot = sum((y - y_bar)**2)
        ss_res = sum((y - f)**2)
        return 1 - ss_res / ss_tot
        


def single_reservoir_pump_pipe_tank_ode_solution(h20,D,d,L,C,tf,pA,pB,dt_max):
    """This produces a numerical solution to a water network that involves
       1 reservoir, 1 pump extracting water from the reservoir, a single pipe
       through which the water runs uphill with frictional losses, and a 
       tank in which the water is stored. The solution involves a single ordinary
       differential equation which is derived from the energy balance, hazen williams
       head loss function, and the derivative of tank head as a function of time
       
       The pump is allowed to pump water until the pump head vs. the water tank
       head reach equillibrium
       
       Inputs:
           h20 - elevation head of the water tank (w/r to the pump head) water
                 surface at time 0 (meters)
           D   - Diameter of the water tank (constant) (meters)
           d   - pipe diameter leading to the water tank (meters)
           L   - pipe length leading to the water tank (meters)
           C   - pipe friction factor (unitless ratio)
           tf  - final time to simulate
           
      Returns 
           Q   - flow through the entire system as a function of time (m3/s)
           t   - time (s)
           h2  - Water tank surface elevation height 
       
       
       """
    
    def S_hazen_will_si(Q,C,d):
        """ returns meters (water) per meter length of pipe"""
        return 10.67 * (Q/C) ** 1.852 / d ** 4.8702
    
    def pump_func(Q,pA,pB):
        
        return pA - pB * Q
    
    def energy_balance_time0(Q,h2,d,D,L,C,pA,pB):
        """ Should balance to zero """
        H2 = h2 + v_head(Q,D)
        H1 = pump_func(Q,pA,pB)
        return H1 - H2 - L * S_hazen_will_si(Q,C,d)
    
    def v_head(Q,diam):
        return (4*Q/(pi*diam**2.0))**2.0 / (2 * 9.81)
    
    def diff_eq(t,Q,d,D,C,L,pB):
        # this can be derived from differentiating the energy balance and considering
        # the head gain integral of the tank becomes dh/dt = Q/A
        # the return is for dQ/dt and dh/dt
        A = pi * D ** 2.0 / 4.0
        return -(Q[0]/A) / (pB + (Q[0] / A**2.0)/9.81 + L * 1.852 * 10.67 * Q[0]**0.852 / (C**1.852 * d**4.8702)), Q[0] / A 
    
    # first solve the initial state 
    Q0_list = [0.1]
    Q0 = fsolve(energy_balance_time0, Q0_list, args=(h20,d,D,L,C,pA,pB))
    
    # make sure the solution is valid!
    assert abs(energy_balance_time0(Q0,h20,d,D,L,C,pA,pB)) <= 0.00001
    
    # now solve the differential equation
    sol = solve_ivp(lambda t,Q:diff_eq(t,Q,d,D,C,L,pB), (0.0,tf),array([Q0[0],h20]),max_step=dt_max)
    t = sol.t
    Q = sol.y[0,:]
    h2 = sol.y[1,:]
    E_lost = zeros(len(h2))
    for i,q in enumerate(Q):
        E_lost[i] = L * S_hazen_will_si(q,C,d)
    
    return Q,t,h2


if __name__ == "__main__":
    unittest.main()