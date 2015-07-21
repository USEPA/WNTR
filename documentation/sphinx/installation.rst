Installation
======================================

Requirements for WNTR include Python 2.7 along with several Python packages and 
Ipopt. WNTR can be installed using git.  More information on installing and 
using git can be found at http://git-scm.com. 

To clone the WNTR repository, use the following command::

	git clone https://software.sandia.gov/git/resilience

Make sure WNTR is on your Python path.  In Python, you can update your
path by using the following command::

	import sys
	sys.path.append('path/to/WNTR')

To permanently add the location of WNTR to your Python path, edit your
environment variables through the Control Panel (System / Advanced / 
Environment / User).  Add the location of WNTR to the PYTHONPATH variable.

.. todo:: The resilience tool should be installed in site-packages and the path should not have to be set....we're working on setup.py now.

Python
------
Information on installing and using python can be found at 
https://www.python.org/.  Python distributions can also be used to manage 
the Python interface.  Python distributions include Python(x,y) (for Windows) 
and Anaconda (for Windows and Linux). These distributions include most of the 
Python packages needed for WNTR, including Numpy, Scipy, NetworkX, Pandas, 
Matplotlib, and Scipy. Pyomo would need to be installed separately.

Python(x,y) can be downloaded from https://code.google.com/p/pythonxy/.  

Anaconda can be downloaded from https://store.continuum.io/cshop/anaconda/.

These Python distributions include tools for code development, numerical 
computations, data analysis and visualization. Python(x,y) is distributed with 
the Spyder IDE (interactive development environment) which includes enhanced 
editing and debug features.  The Spyder IDE includes an editor window, 
console window, and object inspection window in a layout that is very similar 
to using MATLAB. Debugging features are also available from the toolbar.  
Code documentation is displayed in the object inspection 
window, pop-up information on class structure and functions is displayed in the 
editor and console windows.  
Python(x,y) also comes with SciTE, a cross platform text editor designed for 
editing code.  SciTE recognizes many languages (including Python and YML) and 
includes syntax highlighting, indentation, and function recognition. 

Python packages
---------------
The following python packages are required for WNTR:

* Pyomo version X [Hart2014]_: optimization modeling language used for hydraulic simulation, 
  https://software.sandia.gov/trac/pyomo
* Numpy version X: support large, multi-dimensional arrays and matrices, 
  http://www.numpy.org/
* Scipy version X: efficient routines for numerical integration, 
  http://www.scipy.org/
* NetworkX version X [Hagberg2008]_: create and analyze complex networks, 
  https://networkx.github.io/
* Pandas version X [McKinney2013]_: analysis and storage of time series data, 
  http://pandas.pydata.org/
* Matplotlib version X: produce figures, 
  http://matplotlib.org/

The following packages are optional for WNTR:

* Scipy version X: convert units, 
  http://www.sympy.org/en/index.html

All packages can be installed using pip (I think), which is distributed with 
standard Python.  To install Pyomo, for example, use the following command::

	pip install pyomo 

For additional information on using pip, see https://pypi.python.org/pypi/pip.


.. todo:: We can include these dependencies in setup.py

IPOPT
-----
Ipopt (Interior Point OPTimizer) is software for large scale non-linear 
optimization. The Ipopt solver is used in WNTR for hydraulic simulation.  
The HSL library also needs to be installed.

Download Ipopt from http://www.coin-or.org/download/binary/CoinAll/.  

* Select COIN-OR-1.7.4-win32-msvc11.exe for Windows 
* Download and run the executable

Download HSL from http://www.hsl.rl.ac.uk/ipopt/.

* Select Windows or Linux in the COIN-HSL Archive, Personal License box
* Select Personal License, fill out the form and accept
* Download the zip file from the link sent via email
* Extract the files to bin folder for Ipopt.  For example, if Ipopt was saved 
  in C:/Program Files/COIN-OR/1.7.4/win32-msvc11, extract the HSL files to 
  C:/Program Files/COIN-OR/1.7.4/win32-msvc11/bin.
