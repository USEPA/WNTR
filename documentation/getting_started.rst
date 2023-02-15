.. raw:: latex

    \clearpage

.. _getting_started:

Getting started
======================================

To start using WNTR, open a Python console or IDE like Spyder and import the package::

	import wntr	

WNTR comes with a simple `getting started example <https://github.com/USEPA/WNTR/blob/main/examples/getting_started.py>`_, shown below that uses the `EPANET Example Network 3 (Net3) INP file <https://github.com/USEPA/WNTR/blob/main/examples/networks/Net3.inp>`_.
This example demonstrates how to:

* Import WNTR
* Generate a water network model 
* Simulate hydraulics
* Plot simulation results on the network

.. note:: 
   If WNTR is installed using PyPI or Anaconda, the examples folder is not included.  
   The examples folder can be downloaded by going to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
   Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store them in a folder.  
   The following example assumes the user is running the example from the examples folder.

.. literalinclude:: ../examples/getting_started.py

Additional examples are included throughout the WNTR documentation. The examples provided in the documentation assume
that a user has experience using EPANET (https://www.epa.gov/water-research/epanet) and Python (https://www.python.org/), including the ability to install and use additional Python packages, such as those listed in :ref:`requirements` and :ref:`optional_dependencies`.

Several EPANET INP files and example files are also included in the WNTR repository in the `examples folder <https://github.com/USEPA/WNTR/blob/main/examples>`_.
Example networks range from a simple 9 node network to a 3,000 node network.
Additional network models can be downloaded from the University of Kentucky 
Water Distribution System Research Database at
https://uknowledge.uky.edu/wdsrd.

Example files can be run as follows:

* Open a command line or PowerShell prompt and run the example file using Python in interactive mode.  
  This will keep Python open so that graphics can be viewed.  Use ``exit()`` to close Python when done.  
  For example, the getting started example can be run as follows::
  
      python -i getting_started.py
      
* Open a Python console in script mode (no -i) and copy/paste lines of code into the Python console. 
  Use ``exit()`` to close Python when done.

* Open the example file within an IDE like Spyder and run or step through the file. 

    
Additional examples
-----------------------

WNTR comes with additional examples that illustrate advanced use cases, including:

* `Pipe leak, stochastic simulation example <https://github.com/USEPA/WNTR/blob/main/examples/stochastic_simulation.py>`_: 
  This example runs multiple hydraulic simulations of a pipe leak scenario where the location and duration are drawn from probability distributions.
* `Pipe criticality example <https://github.com/USEPA/WNTR/blob/main/examples/pipe_criticality.py>`_: 
  This example runs multiple hydraulic simulations to compute the impact that individual pipe closures have on water pressure.  
* `Fire flow example <https://github.com/USEPA/WNTR/blob/main/examples/fire_flow.py>`_: 
  This example runs hydraulic simulations with and without fire fighting flow demand.
* `Sensor placement example <https://github.com/sandialabs/chama/blob/main/examples/water_network_example.py>`_: 
  This example is hosted in Chama repository (https://github.com/sandialabs/chama) and uses WNTR to optimize the placement of sensors that minimizes detection time. 
  Note that Chama requires Pyomo and a MIP solver, see Chama installation instructions for more details.
  
Additionally, the examples folder contains demonstrations using Jupyter Notebooks. 
A Jupyter Notebook, an open-sourced web-based application, can be accessed through Anaconda or by installing the 
associated software available at https://jupyter.org. These demonstrations include the following: 

* `Pipe break demo <https://github.com/USEPA/WNTR/blob/main/examples/demos/pipe_break_demo.ipynb>`_: 
  This demostration runs multiple hydraulic simulations to compute the impact that different individual pipe breaks/closures have on network pressure. 
  It also plots the pressure and population impacts for all junctions effected by the pipe breaks/closures. 
* `Segment pipe break demo <https://github.com/USEPA/WNTR/blob/main/examples/demos/segment_break_demo.ipynb>`_: 
  This demostration runs multiple hydraulic simulations to compute the impact that different pipe segment breaks/closures (identified by isolation 
  valve locations) have on network pressure. It also plots the pressure and population impacts for all junctions effected by the pipe segment breaks/closures. 
* `Fire flow demo <https://github.com/USEPA/WNTR/blob/main/examples/demos/fire_flow_demo.ipynb>`_: 
  This demostration runs multiple hydraulic simulations with and without fire fighting flow demand to multiple fire hydrant nodes. 
  It also plots the pressure and population impacts for junctions effected by the additional fire fighting flow demand. 
* `Earthquake demo <https://github.com/USEPA/WNTR/blob/main/examples/demos/earthquake_demo.ipynb>`_: 
  This demostration runs hydraulic simulations of earthquake damage with and without repair efforts. It plots fragility curves, 
  peak ground acceleration, peak ground velocity, repair rate, leak probability, and damage states. In addition, it compares 
  junction pressure 24 hours into the simulation, and tank and junction pressure over time. The demonstration also plots water 
  service availability and population impacted by low pressure conditions.
  
For more details about the steps in the demonstrations, review Chapter 12: Water network tool for resilience in 
`Embracing Analytics in the Drinking Water Industry <https://iwaponline.com/ebooks/book/849/Embracing-Analytics-in-the-Drinking-Water-Industry>`_. 
  
  