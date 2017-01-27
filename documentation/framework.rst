.. _software_framework:

Software framework
======================================

Before using WNTR, it is helpful to understand the software framework, features, and limitations.
WNTR uses object oriented programming to 
generate water network models and 
access simulators. 
Water network models can be built from scratch or built directly from EPANET INP files.
Additionally, EPANET INP files can be generated from water network models.
Simulators can access a custom python solver or the EPANET Toolkit [Ross00]_.

The water network model is stored in the :doc:`WaterNetworkModel</apidoc/wntr.network.model>` class.  
This class contains methods to read and write INP files, and access, add, and modify network components.  

WNTR contains two simulators: the 
:doc:`WNTRSimulator</apidoc/wntr.sim.core>` class and the 
:doc:`EpanetSimulator</apidoc/wntr.sim.epanet>` class.
The WNTRSimulator uses custom python solvers to run demand-driven and pressure-driven hydraulic simulation.
The EPANETSimulator uses the EPANET Toolkit to run demand-driven hydraulic simulation and water quality simulation.
The EPANET Toolkit is accessed using the :doc:`pyepanet</apidoc/wntr.epanet.pyepanet>` package, a python extensions for the EPANET Toolkit. 
When using the EPANETSimulator, the water network model is written to temporary EPANET INP file and the 
EPANET Toolkit access that file.  This allows the user to read in INP files, modify the model, run 
an EPANET simulation, and analyze results all within WNTR.
Note that changes to the EPANET model (i.e. changes to supply and demand, valve settings, pump outages) might disrupt the 
ability to successfully run a demand-driven hydraulic simulation.

Software limitations are noted below:

* Certain EPANET model options are not supported in WNTR, as outlined in :numref:`table-framework`.

* Pressure-driven hydraulic simulation and leak models are only available using the WNTRSimulator.  
  Note that the WNTRSimulator can be used to compute demands under pressure-driven conditions and those 
  demands can be used in the EPANETSimulator.  

* Water quality simulations is only available using the EPANETSimulator.  

:numref:`table-framework` lists sections of EPANET INP file and indicates if that section can be 
read into WNTR, 
modified in WNTR, 
used by the WNTRSimulator or EpanetSimulator, and 
written to an EPANET INP file.
All sections that are written to an EPANET INP file can be used by the EpanetSimulator.

.. _table-framework:
.. table:: WNTR supported features and simulation options.

   =================  =================  =================  ===================  =================  =================  
   Sections           Read               Modify	            WNTRSimulator        EPANETSimualtor    Write 
   =================  =================  =================  ===================  =================  =================  
   [TITLE]                                                  NA                   NA
   [JUNCTIONS]         Y
   [RESERVOIRS]        Y
   [TANKS]
   [PIPES]
   [PUMPS]
   [VALVES]
   [EMITTERS]
   [CURVES]
   [PATTERNS]
   [ENERGY]
   [STATUS]
   [CONTROLS]
   [RULES]
   [DEMANDS]
   [QUALITY]
   [REACTIONS]
   [SOURCES]
   [MIXING]
   [OPTIONS]
   [TIMES]
   [REPORT]
   [COORDINATES]
   [VERTICES]
   [LABELS]
   [BACKDROP]
   [TAGS]
   =================  =================  =================  ===================  =================  =================   
