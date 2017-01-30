.. _software_framework:

Software framework
======================================

Before using WNTR, it is helpful to understand the software framework.
WNTR uses object oriented programming. The main classes used to 
generate water network models and 
run simulations are described below, followed by a list of software limitations.

Water network model
----------------------
In WNTR, water network models can be built from scratch or built directly from EPANET INP files.
Additionally, EPANET INP files can be generated from water network models.
The water network model is stored in the :meth:`~wntr.network.model.WaterNetworkModel` class.
The WaterNetworkModel class contains methods to read and write INP files, and access/add/remove/modify network components.
This class links to additional model classes which define network components, controls and model options.

* :meth:`~wntr.network.model.Junction`: Junctions are nodes where links connect. Water can enter or leave the network at a junction.

* :meth:`~wntr.network.model.Reservoir`: Reservoirs are nodes with an infinite external source or sink. 

* :meth:`~wntr.network.model.Tank`: Tanks are nodes with storage capacity. 

* :meth:`~wntr.network.model.Pipe`: Pipes are links that transport water. 

* :meth:`~wntr.network.model.Pump`: Pumps are links that increase hydraulic head. 

* :meth:`~wntr.network.model.Valve`: Valves are links that limit pressure or flow. 

* :meth:`~wntr.network.model.Curve`: Curves are data pairs representing a relationship between two quantities.  Curves are used to define pump curves. 

* :meth:`~wntr.network.controls.TimeControl`: Time controls define actions that start or stop at a particular time. 

* :meth:`~wntr.network.controls.ConditionalControl`: Conditional controls define actions that start or stop based on a particular condition in the network. 

* :meth:`~wntr.network.model.WaterNetworkOptions`: Model options, including the simulation duration and time step.
  
Simulators
---------------
WNTR contains two simulators: the EpanetSimulator and the WNTRSimulator.

* :meth:`~wntr.sim.epanet.EpanetSimulator`: 
  The EpanetSimulator uses the EPANET Toolkit [Ross00]_ to run demand-driven hydraulic simulation and water quality simulation.
  The EPANET Toolkit is accessed using the :meth:`~wntr.epanet.pyepanet` package, a python extensions for the EPANET Toolkit. 
  When using the EPANETSimulator, the water network model is written to an EPANET INP file which is used to run an EPANET simulation.
  This allows the user to read in INP files, modify the model, run 
  an EPANET simulation, and analyze results all within WNTR.
  Note that changes to the EPANET model (i.e. changes to supply and demand, valve settings, pump outages) might disrupt the 
  ability to successfully run a demand-driven hydraulic simulation.

* :meth:`~wntr.sim.core.WNTRSimulator`: The WNTRSimulator uses custom python solvers to run demand-driven and pressure-driven hydraulic simulation
  and includes models to simulate pipe leaks. 

Limitations
---------------
Current software limitations are noted below:

* Certain EPANET model options are not supported in WNTR, as outlined in :numref:`table-framework`.
  This table is updated as new features are added to WNTR.

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
