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
        
        # build up the model to be used in several tests
        h20 = 150.0
                # first test a constant diameter tank!
        inp = {'h20': h20,  # meters
                        'D': 1.0,     # meters
                        'd': 0.2,     # meters
                        'L': sqrt(2) * h20,
                        'C': 130,      # pipe roughness factor
                        'tf': 400.0,   # total simulation time
                        'pA': 200.0,   # pump A coefficient
                        'pB': 4.0,     # pump B coefficient
                        'pC': 1.0,     # pump C coefficient
                        'dt_max':1.0,   # maximum time step for the ode solution
                        'dt_max_wntr':[1,10,50,100]}
        self.ode_inp = inp

        wn = self.wntr.network.WaterNetworkModel()
        
        # build the equivalent WNTR model
        # add nodes 
        
        wn.add_reservoir("r1",base_head=0.0,coordinates=(0,0))
        wn.add_junction("j1",base_demand=0.0,elevation=0.0,coordinates=(0,0))
        wn.add_tank("t1",elevation=h20,init_level=0.0,min_level=0.0,max_level=1.0e10,
                    diameter=inp['D'], min_vol=0.0,coordinates=(h20,0.0))
        # add links
        wn.add_pipe("p1",start_node_name="j1",end_node_name="t1",length=inp['L'],diameter=inp['d'],
                    roughness=inp['C'],minor_loss=0.0)
        wn.add_curve("pump1_curve","HEAD",[(0.0,inp['pA']),(inp['pA']/inp['pB'],0.0)])
        wn.add_pump("pump1",start_node_name="r1",end_node_name="j1",
                    pump_type="HEAD",pump_parameter="pump1_curve",speed=1.0)
        
        wn.options.time.duration=inp['tf']
        wn.options.hydraulic.headloss="H-W"
        wn.options.hydraulic.viscosity=0.0
        wn.options.hydraulic.specific_gravity=1.0
        
        self.wn = wn
        sim = self.wntr.sim.WNTRSimulator(wn)
        
        self.sim = sim
    @classmethod
    def tearDownClass(self):
        pass

    def test_wntr_vs_ode_const_diam(self):
        
        # run the case as set up in the Setup method.
        
        wn = self.wn
        sim = self.sim
        inp = self.ode_inp
        
        # run the wntr model
        results = self._run_study(wn,sim)
        
        # run the ode solution
        Q,t,h2 = single_reservoir_pump_pipe_tank_ode_solution(inp['h20'],
                                                              inp['D'],
                                                              inp['d'],
                                                              inp['L'],
                                                              inp['C'],
                                                              inp['tf'],
                                                              inp['pA'],
                                                              inp['pB'],
                                                              inp['pC'],
                                                              inp['dt_max'])

        hR2 = self._calc_wntr_ode_R2(results[0],t, h2, 'head', 't1', 'node')
#        h_wntr_interp = interp(t,results[0].node['head']['t1'].index,
#                               results[0].node['head']['t1'].values)
#        hR2 = self._R2(h2,h_wntr_interp)
        self.assertLessEqual(0.95,hR2,msg="The WNTR numerical solution for tank head has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")

        QR2 = self._calc_wntr_ode_R2(results[0],t,Q,'flowrate','pump1','link')
        self.assertLessEqual(0.95,QR2,msg="The WNTR numerical solution for flow rate has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")
        
        create_graph = True
        if create_graph:
            self._create_graph(t,Q,h2,inp['dt_max_wntr'],results)
        
    def test_wntr_vs_ode_vcurve(self):
        
        wn = self.wn
        sim = self.sim
        inp = self.ode_inp
        
        # change up the volume curve and make the pump curve nonlinear
        self.ode_inp['vcurve'] = self._vol_curve1()
        self.ode_inp['pC'] = 0.9
        epoint = (inp['pA']/inp['pB'])**(1/inp['pC'])
        pcurve = [(0.0,inp['pA']),
                  (0.5*epoint,inp['pA']-inp['pB']*(0.5*epoint)**inp['pC']),
                  (epoint,0.0)]
        # add the new curves to the model
        wn.add_curve('pcurve','HEAD',pcurve)
        wn.add_curve('vcurve','VOLUME',self.ode_inp['vcurve'])
        # now change the model
        t1 = wn.get_node('t1')
        t1.volume_curve_name = 'vcurve'
        pump1 = wn.get_link('pump1')
        pump1.pump_curve_name = 'pcurve'
        
        results = self._run_study(wn,sim)

        # run the ode solution
        Q,t,h2 = single_reservoir_pump_pipe_tank_ode_solution(inp['h20'],
                                                              inp['D'],
                                                              inp['d'],
                                                              inp['L'],
                                                              inp['C'],
                                                              inp['tf'],
                                                              inp['pA'],
                                                              inp['pB'],
                                                              inp['pC'],
                                                              inp['dt_max'],
                                                        array(inp['vcurve']))
        
        create_graph = True
        if create_graph:
            self._create_graph(t,Q,h2,inp['dt_max_wntr'],results)

        hR2 = self._calc_wntr_ode_R2(results[0],t, h2, 'head', 't1', 'node')

        self.assertLessEqual(0.95,hR2,msg="The WNTR numerical solution for tank head has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")

        QR2 = self._calc_wntr_ode_R2(results[0],t,Q,'flowrate','pump1','link')
        self.assertLessEqual(0.95,QR2,msg="The WNTR numerical solution for flow rate has R2" +
            " value less than 0.95 w/r to solution of an exact differential equation.")
        

        
        
    def _run_study(self,wn,sim):
        results = []
        dt_max_wntr = self.ode_inp['dt_max_wntr']
        for dtmax in dt_max_wntr:
            wn.options.time.hydraulic_timestep=dtmax
            wn.options.time.report_timestep=dtmax
            result = sim.run_sim()
            results.append(result)
            wn.reset_initial_values()
        return results
    
    def _vol_curve1(self):
        """volume curve that has the same volume as the 1meter diameter 
           cylindrical tank at d=50"""
        return [(d,(pi/200.0)*d**2) 
                                for d in arange(0,55)]
    
    def _calc_wntr_ode_R2(self,wntr_res,t,ode_res,var_str,name,attrname):
        wntr_res_attr = getattr(wntr_res,attrname)
        wntr_interp = interp(t,wntr_res_attr[var_str][name].index,
                                   wntr_res_attr[var_str][name].values)
        return self._R2(ode_res,wntr_interp)
    
    def _create_graph(self,t,Q,h2,dt_max_wntr,results):
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
        # head plots
        axl[1].plot(t,h2,label='ode',linewidth=3,linestyle="--")
        for dt,result in zip(dt_max_wntr,results):
            axl[1].plot(result.node['head']['t1'],label="wntr dt={0:4.0f}".format(dt))
        axl[1].set_xlabel('time (s)')
        axl[1].set_ylabel('tank head (m)')
        axl[1].grid("on")
        plt.savefig(join(testdir,"SinglePumpTankExampleWNTRvsODE.png"),dpi=300)
        
        
    def _R2(self,y,f):
        y_bar = mean(y)
        ss_tot = sum((y - y_bar)**2)
        ss_res = sum((y - f)**2)
        return 1 - ss_res / ss_tot
        


def single_reservoir_pump_pipe_tank_ode_solution(h20,D,d,L,C,tf,pA,pB,pC,
                                                 dt_max,vcurve=None):
    """This produces a numerical solution to a water network that involves
       1 reservoir, 1 pump extracting water from the reservoir, a single pipe
       through which the water runs uphill with frictional losses, and a 
       tank in which the water is stored. The solution involves a single ordinary
       differential equation which is derived from the energy balance, hazen williams
       head loss function, and the derivative of tank head as a function of time
       
       The pump is allowed to pump water until the pump head vs. the water tank
       head reach equillibrium
       
       The solution is units dependent and all inputs must be in SI!
       
       Inputs:
           h20 - elevation head of the water tank (w/r to the pump head) water
                 surface at time 0 (meters)
           D   - Diameter of the water tank (constant) (meters)
           d   - pipe diameter leading to the water tank (meters)
           L   - pipe length leading to the water tank (meters)
           C   - pipe friction factor (unitless ratio)
           tf  - final time to simulate (s)
           
      Returns 
           Q   - flow through the entire system as a function of time (m3/s)
           t   - time (s)
           h2  - Water tank surface elevation height 
       
       """
    
    def S_hazen_will_si(Q,C,d):
        """ returns meters (water) per meter length of pipe"""
        return 10.67 * (Q/C) ** 1.852 / d ** 4.8702
    
    def pump_func(Q,pA,pB,pC):
        
        return pA - pB * Q ** pC
    
    def energy_balance_time0(Q,h2,d,D,L,C,pA,pB,pC,vcurve,dh,h20):
        """ Should balance to zero """
        H2 = h2 + v_head(Q,D,h2,vcurve,dh,h20)
        H1 = pump_func(Q,pA,pB,pC)
        return H1 - H2 - L * S_hazen_will_si(Q,C,d)
    
    def v_head(Q,diam,h2,vcurve,dh,h20):
        dVdh2 = dVdh2_func(D,h2,vcurve,dh,h20)
        return (Q/dVdh2)**2.0 / (2 * 9.81)
    
    def dVdh2_func(D,h2,vcurve,dh,h20):
        if vcurve is None:
            dVdh2 = pi * D ** 2.0 / 4.0
        else:
            V0 = interp(h2-h20,vcurve[:,0],vcurve[:,1])
            V1 = interp(h2-h20 + dh,vcurve[:,0],vcurve[:,1])
            dVdh2 = (V1 - V0)/dh
        if dVdh2 == 0.0:
            raise ValueError("The depth-volume curve must not have a zero slope!")
        return dVdh2
    
    def diff_eq(t,x,d,D,C,L,pB,pC,vcurve,dh,h20):
        # this can be derived from differentiating the energy balance and considering
        # the head gain integral of the tank becomes dh/dt = Q/A
        # the return is for dQ/dt and dh/dt
        Q = x[0]
        h2 = x[1]
        dVdh2 = dVdh2_func(D,h2,vcurve,dh,h20)
        
        return (Q/dVdh2) / (pB*pC * Q ** (pC-1.0) - (Q / (dVdh2)**2)/9.81 - L 
                * 1.852 * 10.67 * Q**0.852 / (C**1.852 * d**4.8702)), Q / dVdh2 
    
    
    dh = 0.0000001
    # first solve the initial state 
    Q0_list = [0.1]
    Q0 = fsolve(energy_balance_time0, Q0_list, args=(h20,d,D,L,C,pA,pB,pC,vcurve,dh,h20))
    
    # make sure the solution is valid!
    assert abs(energy_balance_time0(Q0,h20,d,D,L,C,pA,pB,pC,vcurve,dh,h20)) <= 0.00001
    
    # now solve the differential equation
    sol = solve_ivp(lambda t,x:diff_eq(t,x,d,D,C,L,pB,pC,vcurve,dh,h20),
                    (0.0,tf),array([Q0[0],h20]),max_step=dt_max)
    t = sol.t
    Q = sol.y[0,:]
    h2 = sol.y[1,:]
    E_lost = zeros(len(h2))
    for i,q in enumerate(Q):
        E_lost[i] = L * S_hazen_will_si(q,C,d)
    
    return Q,t,h2


if __name__ == "__main__":
    unittest.main()