Installation
======================================

WNTR can be installed as a Python package using standard open source software tools.

**Step 1**: Setup your Python environment

	Python can be installed on Windows, Linux, and Mac OS X operating systems.
	WNTR requires Python (2.7, 3.4, or 3.5) along with several Python package dependencies.
	Python distributions, such as Anaconda, are recommended to manage 
	the Python environment.  Anaconda can be downloaded from https://www.continuum.io/downloads.  
	General information on Python can be found at https://www.python.org/.
	
	Anaconda includes the Python packages needed for WNTR, including Numpy, Scipy, NetworkX, Pandas, and
	Matplotlib.  For more information on Python package dependencies, see :ref:`requirements`.
	
	Anaconda also comes with Spyder, an IDE, that includes enhanced 
	editing and debug features along with a graphical user interface that is very similar 
	to MATLAB. Debugging options are available from the toolbar.  
	Code documentation is displayed in the object inspection 
	window.  Pop-up information on class structure and functions is displayed in the 
	editor and console windows.  

**Step 2**: Install WNTR
	
	The installation process differs for users and developers.  
	Installation instructions for both types are described below.
	
	**For users**: 	Users can install WNTR using pip.  
	pip is a command line software tool used to install and manage Python 
	packages.  pip can be downloaded from https://pypi.python.org/pypi/pip.
	
	To install WNTR using pip, open a command prompt (cmd.exe on Windows, terminal window on Linux) and run::

		pip install wntr
	
	This will install the latest stable version of WNTR from https://pypi.python.org/pypi/wntr.  
	
	.. note:: A WNTR installation using pip will not include the examples folder, which is referenced throughout this manual.  
	
	Users can also download a zip file that includes source files and the examples folder from the USEPA GitHub organization.  
	To download the master (development) branch, go to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP".
	This downloads a zip file called WNTR-master.zip.
	To download a specific release, go to https://github.com/USEPA/WNTR/releases and select a zip file.
	The software can then be installed by running a python script, called setup.py, that is included in the zip file.
	
	To build WNTR from the source files in the zip file, open a command prompt and run::

		unzip WNTR-master.zip
		cd WNTR-master
		python setup.py install
		
	**For developers**: Developers can install and build WNTR from source using git.
	git is a command line software tool for version control and software development.
	git can be downloaded from http://git-scm.com. 
		
	To build WNTR from source using git, open a command prompt and run::

		git clone https://github.com/USEPA/WNTR
		cd wntr
		python setup.py develop
	
	This will install the master (development) branch of WNTR from https://github.com/USEPA/WNTR.
	More information for developers can be found in the :ref:`developers` section.

**Step 3**: Test installation

	To test that WNTR is installed, open Python within a command prompt or by starting an IDE like Spyder and run::
	
		import wntr

	If WNTR is installed properly, python proceeds to the next line. No other output is printed to the screen. 
	
	If WNTR is **not** installed properly, the user will see the following ImportError::
	
		ImportError: No module named wntr
	
.. _requirements:

Requirements
-------------
Requirements for WNTR include Python (2.7, 3.4, or 3.5) along with several Python packages. 
The following Python packages are required:

* Numpy [VaCV11]_: used to support large, multi-dimensional arrays and matrices, 
  http://www.numpy.org/
* Scipy [VaCV11]_: used to support efficient routines for numerical integration, 
  http://www.scipy.org/
* NetworkX [HaSS08]_: used to create and analyze complex networks, 
  https://networkx.github.io/
* Pandas [Mcki13]_: used to analyze and store time series data, 
  http://pandas.pydata.org/
* Matplotlib [Hunt07]_: used to produce figures, 
  http://matplotlib.org/

Optional dependencies
-------------------------

The following Python packages are optional:

* SymPy [JCMG11]_: used to convert units, 
  http://www.sympy.org/en/index.html
* xlwt [Xlwt16]_: used to read/write to Excel spreadsheets,
  http://xlwt.readthedocs.io
* Numpydoc [VaCV11]_: used to build the user manual,
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