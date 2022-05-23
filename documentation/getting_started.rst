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
* `Sensor placement example <https://github.com/USEPA/WNTR/blob/main/examples/sensor_placement.py>`_: 
  This example uses WNTR with Chama (https://chama.readthedocs.io) to optimize the placement of sensors that minimizes detection time. 
  Note that Chama requires Pyomo and a MIP solver, see Chama installation instructions for more details.