Installation
======================================

WNTR can be installed as a Python package using standard open source software tools.

**Step 1**: Setup your Python environment

	WNTR requires Python 2.7 along with several Python package dependencies.
	Python distributions, such as Anaconda, are recommended to manage 
	the Python environment.  Anaconda can be downloaded from https://www.continuum.io/downloads.  
	General information on Python can be found at https://www.python.org/.
	
	Anaconda includes the Python packages needed for WNTR, including Numpy, Scipy, NetworkX, Pandas, 
	Matplotlib, and Sympy.  For more information on Python package dependencies, see :ref:`requirements`.
	
	Anaconda also comes with Spyder, an interactive development environment (IDE), that includes enhanced 
	editing and debug features along with a graphical user interface that is very similar 
	to MATLAB. Debugging options are available from the toolbar.  
	Code documentation is displayed in the object inspection 
	window.  Pop-up information on class structure and functions is displayed in the 
	editor and console windows.  

**Step 2**: Install WNTR

	**For users**: 	Users can install WNTR using pip.  
	pip is a command line software tool used to install and manage Python 
	packages.  The software tool can be downloaded from https://pypi.python.org/pypi/pip.
	
	To install WNTR using pip, run::

		pip install wntr
	
	This will install the latest stable version of WNTR from https://pypi.python.org/pypi/wntr.  

	**For developers**: Developers can install and build WNTR from source using git.
	git is a command line software tool for version control and software development.
	The software tool can be downloaded from http://git-scm.com. 
		
	To build WNTR from source using git, run::

		git clone https://github.com/usepa/wntr
		cd wntr
		python setup.py develop
	
	This will install the development branch of WNTR from https://github.com/uspea/wntr.
	More information for developers can be found in the :ref:`developers` section.

**Step 3**: Test installation

	To test that WNTR is installed, open Python within a command prompt (cmd.exe on Windows) or by starting an IDE like Spyder, and run::
	
		import wntr

.. _requirements:

Requirements
-------------
Requirements for WNTR include Python 2.7 along with several Python packages. 
The following Python packages are required:

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

Optional dependencies
-------------------------

The following Python packages are optional:

* Sympy: used to convert units, 
  http://www.sympy.org/en/index.html
* xlwt: used to read/write to Excel spreadsheets,
  http://xlwt.readthedocs.io
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