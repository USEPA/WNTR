Installation
======================================

Requirements for WNTR include Python 2.7 along with several Python packages and 
Ipopt. WNTR can be installed using git.  More information on installing and 
using git can be found at http://git-scm.com. 

To clone the WNTR repository, use the following commands::

	git clone https://software.sandia.gov/git/resilience
	cd resilience
	python setup.py install

Developers should use the 'develop' option instead of 'install'.  You can also 
clone the git repository using ssh instead of https.

Python
------
Information on installing and using python can be found at 
https://www.python.org/.  Python distributions can also be used to manage 
the Python interface.  Python distributions include Python(x,y) (for Windows) 
and Anaconda (for Windows and Linux). These distributions include most of the 
Python packages needed for WNTR, including Numpy, Scipy, NetworkX, Pandas, 
Matplotlib, and Scipy. Pyomo would need to be installed separately.

Python(x,y) can be downloaded from https://code.google.com/p/pythonxy/.  A 'Full' installation is suggested.

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

* Pyomo version 4.0.9682 [Hart2014]_: optimization modeling language used for hydraulic simulation, 
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

* Sympy version X: convert units, 
  http://www.sympy.org/en/index.html
* Numpydoc version X: build the user manual,
  https://github.com/numpy/numpydoc
  
Most packages can be installed using pip, which is distributed with 
standard Python.  
For additional information on using pip, see https://pypi.python.org/pypi/pip.

IPOPT
-----
Ipopt (Interior Point OPTimizer) is software for large scale non-linear 
optimization. The Ipopt solver is used in WNTR for hydraulic simulation.  
The HSL library also needs to be installed.

Download Ipopt from http://www.coin-or.org/download/binary/CoinAll/.  

* Select COIN-OR-1.7.4-win32-msvc11.exe for Windows 
* Download and run the executable

Download HSL [HSL2013]_ from http://www.hsl.rl.ac.uk/ipopt/.

* Select Windows or Linux in the COIN-HSL Archive, Personal License box
* Select Personal License, fill out the form and accept
* Download the zip file from the link sent via email
* Extract the zip file and save the files to the bin folder for Ipopt.  For example, if Ipopt was saved 
  in C:/Program Files/COIN-OR/1.7.4/win32-msvc11, extract the HSL zip file, copy the files from the extracted folder, and paste them in 
  C:/Program Files/COIN-OR/1.7.4/win32-msvc11/bin.