.. raw:: latex

    \clearpage
	
.. _examples:

Examples
========

The `examples folder <https://github.com/USEPA/WNTR/blob/main/examples>`_ in the WNTR repository includes 
Jupyter Notebook examples, 
Python file examples, and
EPANET INP files that can be used to run analysis in WNTR.

.. note:: 
	   If WNTR is installed using PyPI or Anaconda, the examples folder is not included with the Python package. 
	   The examples can be downloaded by going to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
	   Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store the example files in a folder. 

.. _jupyter_notebooks:

Jupyter Notebook tutorials
--------------------------

WNTR includes several Jupyter Notebooks tutorials.
A Jupyter Notebook, an open-sourced web-based application, can be accessed through Anaconda or by installing the 
associated software available at https://jupyter.org. These tutorials include the following: 

* `Getting started tutorial <https://github.com/USEPA/WNTR/blob/main/examples/getting_started_tutorial.ipynb>`_: 
  This example generates a water network model, simulates hydraulics, and plots simulation results.
* `Basics tutorial <https://github.com/USEPA/WNTR/blob/main/examples/basics_tutorial.ipynb>`_: 
  This tutorial runs through several basic operations in WNTR, including 
  building and modifying a water network model, 
  running a hydraulic simulation, 
  computing resilience metrics, 
  defining fragility curves, 
  skeletonizing a water network model, and
  geospatial capabilities.
* `Model development tutorial <https://github.com/USEPA/WNTR/blob/main/examples/model_development_tutorial.ipynb>`_: 
  This tutorial creates a water network model using imperfect geospatial data of a water distribution system.
* `Pipe break tutorial <https://github.com/USEPA/WNTR/blob/main/examples/pipe_break_tutorial.ipynb>`_: 
  This tutorial runs multiple hydraulic simulations to compute the impact that different individual pipe breaks/closures have on network pressure. 
  It also plots the pressure and population impacts for all junctions affected by the pipe breaks/closures. 
* `Pipe segments tutorial <https://github.com/USEPA/WNTR/blob/main/examples/pipe_segments_tutorial.ipynb>`_: 
  This tutorial defines isolation valves and pipe segments, then runs multiple hydraulic simulations to compute 
  the impact that different pipe segment closures have on network pressure. 
* `Fire flow tutorial <https://github.com/USEPA/WNTR/blob/main/examples/fire_flow_tutorial.ipynb>`_: 
  This tutorial runs multiple hydraulic simulations with and without fire fighting flow demand to multiple fire hydrant nodes. 
  It also plots the pressure and population impacts for junctions affected by the additional fire fighting flow demand. 
* `Earthquake tutorial <https://github.com/USEPA/WNTR/blob/main/examples/earthquake_tutorial.ipynb>`_: 
  This tutorial runs hydraulic simulations of earthquake damage with and without repair efforts. It plots fragility curves, 
  peak ground acceleration, peak ground velocity, repair rate, leak probability, and damage states. In addition, it compares 
  junction pressure 24 hours into the simulation, and tank and junction pressure over time. The tutorial also plots water 
  service availability and population impacted by low pressure conditions.
* `Salt water intrusion tutorial <https://github.com/USEPA/WNTR/blob/main/examples/salt_water_intrusion_tutorial.ipynb>`_: 
  This tutorial uses storm surge raster data to estimate salt intrusion 
  into a system after a hurricane.
* `Landslide tutorial <https://github.com/USEPA/WNTR/blob/main/examples/landslide_tutorial.ipynb>`_: 
  This tutorial uses GIS data to quantify potential water service disruptions from pipes damaged in a landslide.
* `Multispecies water quality tutorial <https://github.com/USEPA/WNTR/blob/main/examples/multispecies_tutorial.ipynb>`_: 
  This tutorial uses EPANET-MSX to model multispecies chlorine decay.

To open a Jupyter Notebook tutorial (in this case, the getting started tutorial), run the following command::
	
	jupyter lab getting_started_tutorial.ipynb
	
The Jupyter Notebook will open in a browser (e.g., Chrome, Firefox) and the example can be run using 'Run' button.  
Additional information on Jupyter Notebooks is available at https://jupyter.org.

For more details about the steps in the pipe break and fire flow tutorials, review Chapter 12: Water network tool for resilience in 
`Embracing Analytics in the Drinking Water Industry <https://iwaponline.com/ebooks/book/849/Embracing-Analytics-in-the-Drinking-Water-Industry>`_. 

	   
Python file examples
--------------------
WNTR also comes with Python code examples that illustrate several use cases, including:

* `Getting started example <https://github.com/USEPA/WNTR/blob/main/examples/getting_started.py>`_: 
  This example generates a water network model, simulates hydraulics, and plots simulation results.
* `Pipe leak, stochastic simulation example <https://github.com/USEPA/WNTR/blob/main/examples/stochastic_simulation.py>`_: 
  This example runs multiple hydraulic simulations of a pipe leak scenario where the location and duration are drawn from probability distributions.
* `Pipe criticality example <https://github.com/USEPA/WNTR/blob/main/examples/pipe_criticality.py>`_: 
  This example runs multiple hydraulic simulations to compute the impact that individual pipe closures have on water pressure.  
* `Fire flow example <https://github.com/USEPA/WNTR/blob/main/examples/fire_flow.py>`_: 
  This example runs hydraulic simulations with and without fire fighting flow demand.
* `Sensor placement example <https://github.com/sandialabs/chama/blob/main/examples/water_network_example.py>`_: 
  This example is hosted in Chama repository (https://github.com/sandialabs/chama) and uses WNTR to optimize the placement of sensors that minimizes detection time. 
  Note that Chama requires Pyomo and a MIP solver, see Chama installation instructions for more details.

Example files can be run as follows:

* Open a command line or PowerShell prompt and run the example file using Python in interactive mode.  
  This will keep Python open so that graphics can be viewed.  Use ``exit()`` to close Python when done.  
  For example, the getting started example can be run as follows::
  
      python -i getting_started.py
      
* Open a Python console in script mode (no -i) and copy/paste lines of code into the Python console. 
  Use ``exit()`` to close Python when done.

* Open the example file within an IDE like Spyder and run or step through the file. 

EPANET INP files
-------------------

Several EPANET INP files and Python code example files are also included in the `examples folder <https://github.com/USEPA/WNTR/blob/main/examples>`_.
Example EPANET INP files are for networks that range from a simple 9 node network to a 3,000 node network.
Additional network model files can be downloaded from the University of Kentucky 
Water Distribution System Research Database at
https://uknowledge.uky.edu/wdsrd.
