.. raw:: latex

    \clearpage

.. _installation:

Installation
======================================
.. include:: <isonum.txt>

WNTR requires 64-bit Python (tested on versions 3.9, 3.10, 3.11, and 3.12) along with several 
Python package dependencies. 
See :ref:`requirements` for more information.
WNTR can be installed as a Python package as briefly described below. 
:ref:`detailed_instructions` are included in the following section.

The latest release of WNTR can be installed from PyPI or Anaconda using one of the 
following commands in a terminal, command line, or PowerShell prompt. 

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
.. |pypi downloads| image:: https://static.pepy.tech/badge/wntr
.. _pypi downloads: https://pepy.tech/project/wntr
.. |anaconda version| image:: https://anaconda.org/conda-forge/wntr/badges/version.svg 
.. _anaconda version: https://anaconda.org/conda-forge/wntr
.. |anaconda downloads| image:: https://anaconda.org/conda-forge/wntr/badges/downloads.svg
.. _anaconda downloads: https://anaconda.org/conda-forge/wntr

	
.. _detailed_instructions:

Detailed instructions
-------------------------

Detailed installation instructions are included below.

Step 1: Setup the Python environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	Python can be installed on Windows, Linux, and Mac OS X operating systems.
	WNTR requires 64-bit Python (tested on versions 3.9, 3.10, 3.11, and 3.12) along with several Python package dependencies.
	Python distributions, such as Anaconda, are recommended to manage 
	the Python environment.  Anaconda can be downloaded from https://www.anaconda.com/products/individual.
	Additional instructions for setting up a Python environment independent of Anaconda are available at https://docs.python.org/.
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
		 
	Anaconda includes the Python packages needed for WNTR, including NumPy, SciPy, NetworkX, Pandas, and
	Matplotlib.  For more information on Python package dependencies, see :ref:`requirements`.
	If the Python installation does not include these dependencies, the user will need to install them. 
	This is most commonly done using pip or conda. 
	Detailed guidance concerning package installation using pip is available at https://packaging.python.org/.
	
	Anaconda also comes with Spyder, an IDE, that includes enhanced 
	editing and debugging features along with a graphical user interface. 
	The IDE provides debugging options accessible from the toolbar, 
	displays code documentation in the object inspection window, and 
	shows pop-up information on class structure and functions in the 
	editor and console windows. Non-Anaconda users can download 
	Spyder from https://www.spyder-ide.org/. 
	For a detailed installation guide, please refer to https://docs.spyder-ide.org/.
	
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

	WNTR can be installed using PyPI, Anaconda, or by downloading 
	a zip file and building the source code, as described below.
	Information for developers can be found in the :ref:`developer_instructions` section.
	
	.. note:: 
	   If WNTR is installed using PyPI or Anaconda (Options 1 or 2 below), the examples folder is not included with the Python package.   
	   The examples can be downloaded by going to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
	   Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store the example files in a folder. 
	   
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
	  
	* **Option 3**: Users can download and build WNTR using source files from the WNTR GitHub repository.  
	  
	  To download a zip file of the main branch, go to https://github.com/USEPA/WNTR, select the "Clone or download" button and then select "Download ZIP."
	  This downloads a file called WNTR-main.zip.
	  To download a specific release, go to https://github.com/USEPA/WNTR/releases and select a zip file.
	  The zip file contains the examples folder.
	  
	  Uncompress the zip file using standard software tools (e.g., unzip, WinZip) and store them in a folder. 
	  WNTR can then be installed using pip, which is a command line software tool used to install and manage Python 
	  packages.  It can be downloaded from https://pypi.python.org/pypi/pip.
	  To build WNTR from the source files, open a command line or PowerShell prompt from within the folder that contains the ``setup.py`` file and run:: 
	  
		  python -m pip install .
	
	  This runs ``setup.py install``. The ``-m`` option runs pip as a Python script. 
	  The ``.`` indicates that the source files are in the current directory.
	  This use of pip installs WNTR using the local source files (not from PyPI as shown in Option 1).
	   
	  .. note:: 
	     WNTR includes C++ code that is built into shared object files (e.g., pyd for Windows)
	     during the setup process. This requires that the user has a C++ compiler (e.g., Visual Studio C++, GNU C++, MinGW) on their path.
	     No compiler is needed when installing WNTR through PyPI (Option 1) or conda (Option 2). 
   

.. note:: Mac builds and EPANETMSX

   The builds of EPANETMSX for Mac require the OpenMP package be installed. This is easiest to do using
   homebrew. A brew recipe is provided with WNTR that will obtain the appropriate libraries. To use it,
   download the https://github.com/USEPA/WNTR/tree/main/wntr/epanet/libepanet/darwin-formula/libomp.rb 
   formula directly and brew it, or use the command below.
   This should install the necessary libraries onto your machine to be able to run WNTR with EPANETMSX extensions.

   .. code:: bash
	  
	  brew reinstall --build-from-source --formula https://github.com/USEPA/WNTR/tree/main/wntr/epanet/libepanet/darwin-formula/libomp.rb
	 

Step 3: Test installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	To test that WNTR is installed, open a Python console and run::
	
		import wntr

	If WNTR is installed properly, Python proceeds to the next line. No other output is printed to the screen. 
	
	If WNTR is **not** installed properly, the user will see the following ImportError::
	
		ImportError: No module named wntr
	
	To verify the version of WNTR that has been installed, continue in the Python console and run::
	
		print(wntr.__version__)
		
	This will print the WNTR version to the screen, for example, "1.0.0".
	
	See :ref:`getting_started` for a simple example that can also be used to test installation.
	A full set of software tests can also be run locally to ensure proper installation, see :ref:`software_tests` for more details.

.. _developer_instructions:

Developer instructions
------------------------

Developers should review the :ref:`developers` section before contributing to WNTR.

Developers can clone and setup the main branch of WNTR from source files 
using the following commands in a terminal, command line, or PowerShell prompt::

    git clone https://github.com/USEPA/WNTR
    cd WNTR
    python -m pip install -e .
    pip install -r requirements.txt

The ``-e`` option runs ``setup.py develop``.
This will install the main branch of WNTR from https://github.com/USEPA/WNTR in development mode.
The ``requirements.txt`` file contains all the necessary dependencies for testing the package
and building the documentation.

.. note:: 
   WNTR includes C++ code that is built into shared object files (e.g., pyd for Windows)
   during the setup process. This requires that the developer has a C++ compiler located in a folder specified in their PATH.
   When installing WNTR through PyPI or conda, the shared object files do not need to be built 
   and no compiler is needed.

If the developer does NOT have a C++ compiler, or would rather use prebuilt wheels (a pre-built binary package format for Python modules and libraries),
the shared object files can be downloaded from WNTR GitHub Actions using the following steps:

* Clone and setup the main branch of WNTR from the GitHub 
  repository using the following commands in a terminal, command line, or PowerShell prompt 
  (the ``--no-build`` command line argument omits the build step in the setup process)::

    git clone https://github.com/USEPA/WNTR
    cd WNTR
    python -m pip install -e . --no-build
    pip install -r requirements.txt
	
* Select the latest GitHub Actions build_tests that uses the main branch from https://github.com/USEPA/WNTR/actions/workflows/build_tests.yml
* Scroll down to "Artifacts"
* Download the wheel that matches the desired operating system and Python version (for example, wntr_3.9_windows-latest.whl)
* Unzip the wheel and locate the following files (which are named according to the operating system and Python version)

   * wntr/sim/aml/_evaluator.cp39-win_amd64.pyd
   * wntr/sim/network_isolation/_network_isolation.cp39-win_amd64.pyd
   
* Copy these files into the matching directory in the cloned version of WNTR

To test WNTR, developers can run software tests locally using the following command::
	
	pytest wntr

.. _requirements:

Requirements
-------------

Requirements for WNTR include 64-bit Python (tested on versions 3.9, 3.10, 3.11, and 3.12) along with several Python packages. 
Users should have experience using Python (https://www.python.org/), including the installation of additional Python packages. 

**The following Python packages are required**:

* NumPy :cite:p:`vacv11`: used to support large, multi-dimensional arrays and matrices, 
  http://www.numpy.org/
* SciPy :cite:p:`vacv11`: used to support efficient routines for numerical integration, 
  http://www.scipy.org/
* NetworkX :cite:p:`hass08`: used to create and analyze complex networks, 
  https://networkx.github.io/
* pandas :cite:p:`mcki13`: used to analyze and store time series data, 
  http://pandas.pydata.org/
* Matplotlib :cite:p:`hunt07`: used to produce graphics, 
  http://matplotlib.org/
* Setuptools: used to install the WNTR package, https://setuptools.pypa.io/
  
**The following Python packages are optional**:

* plotly :cite:p:`sphc16`: used to produce interactive scalable graphics, 
  https://plot.ly/
* folium :cite:p:`folium`: used to produce Leaflet maps, 
  http://python-visualization.github.io/folium/
* utm :cite:p:`bieni19`: used to translate node coordinates to utm and lat/long,
  https://pypi.org/project/utm/
* geopandas :cite:p:`jvfm21`: used to work with geospatial data,
  https://geopandas.org/
* rasterio :cite:p:`rasterio`: used to work with raster data,
  https://rasterio.readthedocs.io/
* rtree :cite:p:`rtree`: used for overlay operations in geopandas,
  https://rtree.readthedocs.io/
* openpyxl :cite:p:`gacl18`: used to read/write to Microsoft® Excel® spreadsheets,
  https://openpyxl.readthedocs.io
* Additional optional packages listed in `requirements.txt <https://github.com/USEPA/WNTR/blob/main/requirements.txt>`_ are used to build documentation and run tests.

All of these packages are included in the Anaconda Python distribution.
Version requirements are included in `requirements.txt <https://github.com/USEPA/WNTR/blob/main/requirements.txt>`_.
 
To install required and optional dependencies, run::

	pip install -r requirements.txt
