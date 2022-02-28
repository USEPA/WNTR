.. raw:: latex

    \clearpage

Installation
======================================
.. include:: <isonum.txt>

WNTR requires 64-bit Python (tested on versions 3.6, 3.7, 3.8, and 3.9) along with several 
Python package dependencies. 
See :ref:`requirements` and :ref:`optional_dependencies` for more information.
WNTR can be installed as a Python package as briefly described below. 
:ref:`detailed_instructions` are included in the following section.

Users can install the latest release of WNTR from PyPI or Anaconda using one of the following commands in a command line or PowerShell prompt.

.. only:: html

   * PyPI |pypi version|_ |pypi downloads|_ ::

       pip install wntr

   * Anaconda |anaconda version|_ |anaconda downloads|_ ::

       conda install -c conda-forge wntr

.. only:: latex

   * PyPI::

       pip install wntr

   * Anaconda::

       conda install -c conda-forge wntr


.. |pypi version| image:: https://img.shields.io/pypi/v/wntr.svg?maxAge=3600
.. _pypi version: https://pypi.org/project/wntr/
.. |pypi downloads| image:: https://pepy.tech/badge/wntr
.. _pypi downloads: https://pepy.tech/project/wntr
.. |anaconda version| image:: https://anaconda.org/conda-forge/wntr/badges/version.svg 
.. _anaconda version: https://anaconda.org/conda-forge/wntr
.. |anaconda downloads| image:: https://anaconda.org/conda-forge/wntr/badges/downloads.svg
.. _anaconda downloads: https://anaconda.org/conda-forge/wntr

Developers can install the main branch of WNTR from the GitHub 
repository using the following commands in a command line or PowerShell prompt::

    git clone https://github.com/USEPA/WNTR
    cd WNTR
    python setup.py develop

More information for developers can be found in the :ref:`developers` section.

.. _detailed_instructions:

Detailed instructions
-------------------------

Detailed installation instructions are included below.

Step 1: Setup the Python environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	Python can be installed on Windows, Linux, and Mac OS X operating systems.
	WNTR requires 64-bit Python (tested on versions 3.6, 3.7, 3.8, and 3.9) along with several Python package dependencies.
	Python distributions, such as Anaconda, are recommended to manage 
	the Python environment.  Anaconda can be downloaded from https://www.anaconda.com/products/individual.
	General information on Python can be found at https://www.python.org/.
	
	.. note:: 
	   * It is recommended to install Anaconda for a single user by selecting the 'Just Me' option during installation. 
	     If a user-writeable location is selected for installation (e.g., C:\\Users\\username\\Anaconda3), then 
	     the 'Just Me' option does not require administrator privileges.  
	   * It is also recommended to add Anaconda to the PATH environment variable. This will facilitate access to Python from a command prompt 
	     without having to include the full path name.
	     This can be done by either 1) selecting the 'Add Anaconda to my PATH environment variable' option during installation or 2) manually adding C:\\Users\\username\\Anaconda3 to the environmental variables.
	     Note that the first option is not recommended by Anaconda because it elevates the priority of Anaconda software over previously installed software.
	     While the second option allows the user to define priority, this requires administrator privileges. 
	     If Anaconda is not added to the PATH environment variable, Python can be run by using the full path name (e.g., C:\\Users\\username\\Anaconda3\\python).
		 
	Anaconda includes the Python packages needed for WNTR, including NumPy, SciPy, NetworkX, pandas, and
	Matplotlib.  For more information on Python package dependencies, see :ref:`requirements`.
	If the Python installation does not include these dependencies, the user will need to install them. 
	This is most commonly done using pip or conda. 
	
	Anaconda also comes with Spyder, an IDE, that includes enhanced 
	editing and debugging features along with a graphical user interface. 
	Debugging options are available from the toolbar.  
	Code documentation is displayed in the object inspection 
	window.  Pop-up information on class structure and functions are displayed in the 
	editor and console windows.  
	
	To open a Python console, open a command prompt (cmd.exe on Windows, terminal window on Linux and Mac OS X) 
	and run 'python', as shown in :numref:`fig-cmd-python`, 
	or open a Python console using an IDE, like Spyder, as shown in :numref:`fig-spyder`.
	
	.. _fig-cmd-python:
	.. figure:: figures/cmd_python.png
	   :width: 891
	   :alt: Python
	   
	   Python console opened from a command prompt.
   
	.. _fig-spyder:
	.. figure:: figures/spyder.png
	   :width: 759
	   :alt: Spyder
	   
	   Python console using Spyder.
	   
Step 2: Install WNTR
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	The installation process differs for users and developers.  
	Installation instructions for both types are described below.
	
	**For users**: Users can install WNTR using PyPI, Anaconda, or by downloading a zip file and building the source code.
	
	.. note:: 
	   If WNTR is installed using PyPI or Anaconda (Options 1 or 2 below), the examples folder will not be downloaded.  
	   The examples can be downloaded by going to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
	   Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store them in a folder. 
	   
	* **Option 1**: Users can install WNTR from PyPI using pip, which is a command line software tool used to install and manage Python 
	  packages.  It can be downloaded from https://pypi.python.org/pypi/pip.
	
	  To install WNTR using pip, open a command line or PowerShell prompt and run::

		  pip install wntr
	
	  This will install the latest release of WNTR from https://pypi.python.org/pypi/wntr.  
	
	* **Option 2**: Users can install WNTR from Anaconda using conda, which is a command line software tool used to install and manage Python 
	  packages.  It can be downloaded from https://www.anaconda.com/products/individual.
	
	  To install WNTR using conda, open a command line or PowerShell prompt and run::

		  conda install -c conda-forge wntr
	
	  This will install the latest release of WNTR from https://anaconda.org/conda-forge/wntr.
	  
	* **Option 3**: Users can download a zip file that includes source files and the examples folder from the US EPA GitHub organization.  
	  
	  To download the main branch, go to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
	  This downloads a zip file called WNTR-main.zip.
	  
	  To download a specific release, go to https://github.com/USEPA/WNTR/releases and select a zip file.
	  
	  Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store them in a folder. 
	  WNTR can then be installed by running a Python script, called setup.py, that is included in the source files.
	  To build WNTR from the source files, open a command line or PowerShell prompt from within the folder that contains the files and run:: 
	  
		  python setup.py install
	
	**For developers**: Developers can install and build WNTR from source files using git, which 
	is a command line software tool for version control and software development.
	It can be downloaded from http://git-scm.com. 
		
	To build WNTR from source files using git, open a command line or PowerShell prompt and run::

		git clone https://github.com/USEPA/WNTR
		cd WNTR
		python setup.py develop
	
	This will install the main branch of WNTR from https://github.com/USEPA/WNTR.
	More information for developers can be found in the :ref:`developers` section.

Step 3: Test installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	To test that WNTR is installed, open a Python console and run::
	
		import wntr

	If WNTR is installed properly, Python proceeds to the next line. No other output is printed to the screen. 
	
	If WNTR is **not** installed properly, the user will see the following ImportError::
	
		ImportError: No module named wntr
	
	See :ref:`getting_started` for a simple example that can also be used to test installation.
	A full set of software tests can also be run locally to ensure proper installation, see :ref:`software_tests` for more details.
	
.. _requirements:

Requirements
-------------

Requirements for WNTR include 64-bit Python (tested on versions 3.6, 3.7, 3.8, and 3.9) along with several Python packages. 
Users should have experience using Python (https://www.python.org/), including the installation of additional Python packages. The following Python packages are required:


* NumPy [VaCV11]_: used to support large, multi-dimensional arrays and matrices, 
  http://www.numpy.org/
* SciPy [VaCV11]_: used to support efficient routines for numerical integration, 
  http://www.scipy.org/
* NetworkX [HaSS08]_: used to create and analyze complex networks, 
  https://networkx.github.io/
* pandas [Mcki13]_: used to analyze and store time series data, 
  http://pandas.pydata.org/
* Matplotlib [Hunt07]_: used to produce graphics, 
  http://matplotlib.org/
  
These packages are included in the Anaconda Python distribution.
 
.. _optional_dependencies:

Optional dependencies
-------------------------

The following Python packages are optional:

* plotly [SPHC16]_: used to produce interactive scalable graphics, 
  https://plot.ly/
* folium [Folium]_: used to produce Leaflet maps, 
  http://python-visualization.github.io/folium/
* utm [Bieni19]_: used to translate node coordinates to utm and lat/long,
  https://pypi.org/project/utm/
* openpyxl [GaCl18]_: used to read/write to Microsoft® Excel® spreadsheets,
  https://openpyxl.readthedocs.io
* numpydoc [VaCV11]_: used to build the user manual,
  https://github.com/numpy/numpydoc
* nose: used to run software tests,
  http://nose.readthedocs.io

These packages are included in the Anaconda Python distribution.

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
