Installation (*DRAFT*)
======================================

WNTR can be installed as a python package using pip or from source using git.  
More information on pip can be found at https://pypi.python.org/pypi/pip.
More information on git can be found at http://git-scm.com. 

To install using pip (**NOT COMPLETE**)::

	pip install wntr
	
To build WNTR from source using an SSH or HTTPS protocol (**NOT COMPLETE**)::

	git clone https://github.com/usepa/wntr
	cd resilience
	python setup.py install

Developers can build WNTR in development mode::
	
	git clone https://github.com/usepa/wntr
	cd resilience
	python setup.py develop
	
Requirements
-------------
Requirements for WNTR include Python 2.7 along with several Python packages. 

Python
^^^^^^^
Information on installing and using python can be found at 
https://www.python.org/.  Python distributions can also be used to manage 
the Python interface.  Python distributions include Python(x,y) (for Windows) 
and Anaconda (for Windows and Linux). These distributions include most of the 
Python packages needed for WNTR, including Numpy, Scipy, NetworkX, Pandas, 
Matplotlib, and Sympy. 

Python(x,y) can be downloaded from http://python-xy.github.io/.  

Anaconda can be downloaded from https://store.continuum.io/cshop/anaconda/.

Python distributions include several tools for code development (i.e. Spyder, SciTE), 
numerical computations, data analysis and visualization. 
Spyder is an interactive development environment that includes enhanced 
editing and debug features along with a layout that is very similar 
to using MATLAB. Debugging features are also available from the toolbar.  
Code documentation is displayed in the object inspection 
window, pop-up information on class structure and functions is displayed in the 
editor and console windows.  
SciTE is a cross platform text editor designed for 
editing code.  SciTE recognizes many languages (including Python and YML) and 
includes syntax highlighting, indentation, and function recognition. 

Python packages
^^^^^^^^^^^^^^^^^
The following python packages are required for WNTR:

* Numpy [vanderWalt2011]_: used to support large, multi-dimensional arrays and matrices, 
  http://www.numpy.org/
* Scipy [vanderWalt2011]_: used to support efficient routines for numerical integration, 
  http://www.scipy.org/
* NetworkX [Hagberg2008]_: used to create and analyze complex networks, 
  https://networkx.github.io/
* Pandas [McKinney2013]_: used to analyze and store time series data, 
  http://pandas.pydata.org/
* Matplotlib [Hunter2007]_: used to produce figures, 
  http://matplotlib.org/

Packages can be installed using pip.

Optional dependencies
-------------------------

The following python packages are optional for WNTR:

* Sympy: used to convert units, 
  http://www.sympy.org/en/index.html
* Numpydoc [vanderWalt2011]_: used to build the user manual,
  https://github.com/numpy/numpydoc

.. The following is not shown in the UM
   WNTR includes a beta version of a Pyomo hydraulic simulator which requires installing 
   Pyomo, Interior Point OPTimizer (Ipopt), and HSL.

   * Pyomo [Hart2014]_: optimization modeling language and optimization capabilities, https://software.sandia.gov/trac/pyomo.  
     Version 4.0.9682 is recommended.
   * Ipopt: large scale non-linear optimization, http://www.coin-or.org/download/binary/CoinAll/.  
   
	* Select COIN-OR-1.7.4-win32-msvc11.exe for Windows 
	* Download and run the executable

   * HSL [HSL2013]_: solvers for Ipopt, http://www.hsl.rl.ac.uk/ipopt/.
	
	* Select Windows or Linux in the COIN-HSL Archive, Personal License box
	* Select Personal License, fill out the form and accept
	* Download the zip file from the link sent via email
	* Extract the zip file and save the files to the bin folder for Ipopt.  For example, if Ipopt was saved 
	  in C:/Program Files/COIN-OR/1.7.4/win32-msvc11, extract the HSL zip file, copy the files from the extracted folder, and paste them in 
	  C:/Program Files/COIN-OR/1.7.4/win32-msvc11/bin.