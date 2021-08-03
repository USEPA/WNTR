.. raw:: latex

    \clearpage

.. _criticality:

Criticality analysis
================================

WNTR can be used for both threat agnostic and threat informed resilience analysis.  
The section on :ref:`disaster` describes methods to model threat informed damage to water distribution systems.
In threat agnostic analysis, the cause of the disruption is not modeled directly.  
Rather, a series of simulations can be used to perform N-k contingency analysis, where N is the number 
of elements and k elements fail.

In water distribution systems analysis, N-1 contingency analysis is commonly called criticality analysis [WaWC06]_.
WNTR is commonly used to run criticality analysis, where a series of simulations are run to determine the impact of 
individuals failures on the system.  
This framework can be expanded to include analysis where 2 or more elements fail at one time or in succession.
Metrics such as water service availability and water pressure are commonly used 
to quantify impact.  Analysis can include the different components, including:

* Pipe criticality
* Pump criticality
* Segment criticality (based on valve isolation, see ref:`valvelayer: for more details)
* Fire flow criticality

In each case, a single element is changed in each simulation.  
The pipe, pump, or segment is closed in the case of pipe, pump, and segment criticality.
Demand at hydrants is increased in the case of fire flow criticality.
Summary metrics are collected for each simulation to determine the relative impact of each simulation.

The `pipe criticality example <https://github.com/USEPA/WNTR/blob/main/examples/pipe_criticality.py>`_ 
runs multiple hydraulic simulations to compute the impact that individual pipe closures have on water pressure.  
