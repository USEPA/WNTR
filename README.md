![WNTR](documentation/figures/logo.png)
=======================================

[![build](https://github.com/USEPA/WNTR/workflows/build/badge.svg)](https://github.com/USEPA/WNTR/actions/workflows/build_tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/USEPA/WNTR/badge.svg?branch=main)](https://coveralls.io/github/USEPA/WNTR?branch=main)
[![Documentation Status](https://readthedocs.org/projects/wntr/badge/?version=latest)](https://wntr.readthedocs.io/en/latest/?badge=latest)

The Water Network Tool for Resilience (WNTR) is a Python package designed to simulate and 
analyze resilience of water distribution networks. The software includes capability to:

* Generate water network models
* Modify network structure and operations
* Add disruptive events including pipe leaks
* Add response/repair strategies
* Simulate pressure dependent demand and demand-driven hydraulics
* Simulate water quality 
* Evaluate resilience 
* Visualize results

For more information, go to http://wntr.readthedocs.io

Installation
--------------

The latest release of WNTR can be installed from PyPI or Anaconda using one of the following commands in a command line or PowerShell prompt.

* PyPI [![version](https://img.shields.io/pypi/v/wntr.svg?maxAge=3600)](https://pypi.org/project/wntr/) [![Downloads](https://pepy.tech/badge/wntr)](https://pepy.tech/project/wntr)

  ``pip install wntr``
  
* Anaconda [![version](https://anaconda.org/conda-forge/wntr/badges/version.svg)](https://anaconda.org/conda-forge/wntr) [![downloads](https://anaconda.org/conda-forge/wntr/badges/downloads.svg)](https://anaconda.org/conda-forge/wntr)

  ``conda install -c conda-forge wntr``
  
Additional instructions are available at https://wntr.readthedocs.io/en/latest/installation.html.

Citing WNTR
-----------------

To cite WNTR, use one of the following references:

* Klise, K.A., Murray, R., Haxton, T. (2018). An overview of the Water Network Tool for Resilience (WNTR), In Proceedings of the 1st International WDSA/CCWI Joint Conference, Kingston, Ontario, Canada, July 23-25, 075, 8p.

* Klise, K.A., Bynum, M., Moriarty, D., Murray, R. (2017). A software framework for assessing the resilience of drinking water systems to disasters with an example earthquake case study, Environmental Modelling and Software, 95, 420-431, doi: 10.1016/j.envsoft.2017.06.022

* Klise, K.A., Hart, D.B., Moriarty, D., Bynum, M., Murray, R., Burkhardt, J., Haxton, T. (2017). Water Network Tool for Resilience (WNTR) User Manual, U.S. Environmental Protection Agency Technical Report, EPA/600/R-17/264, 47p.

License
------------

WNTR is released under the Revised BSD license.  See the LICENSE.txt file.

Organization
------------

Directories
  * wntr - Python package
  * documentation - User manual
  * examples - Examples and network files
  * ci - Software requirements for continuous integration testing
  
Contact
--------

   * Katherine Klise, Sandia National Laboratories, kaklise@sandia.gov
   * Terra Haxton, US Environmental Protection Agency, haxton.terra@epa.gov
   * Regan Murray, US Environmental Protection Agency, murray.regan@epa.gov

EPA Disclaimer
-----------------

The United States Environmental Protection Agency (EPA) GitHub project code is provided on an "as is" 
basis and the user assumes responsibility for its use. EPA has relinquished control of the information and 
no longer has responsibility to protect the integrity , confidentiality, or availability of the information. Any 
reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, 
or otherwise, does not constitute or imply their endorsement, recommendation or favoring by EPA. The EPA 
seal and logo shall not be used in any manner to imply endorsement of any commercial product or activity 
by EPA or the United States Government.

Sandia Funding Statement
--------------------------------

Sandia National Laboratories is a multimission laboratory managed and operated by National Technology and 
Engineering Solutions of Sandia, LLC., a wholly owned subsidiary of Honeywell International, Inc., for the 
U.S. Department of Energy's National Nuclear Security Administration under contract DE-NA-0003525.
