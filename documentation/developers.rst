.. _developers:

Developers (*DRAFT*)
====================

The following section includes information about 
the software repository, 
software tests and documentation, and 
ways to contribute and request new features.

GitHub repository
---------------------
WNTR is hosted on USEPA GitHub organization at https://github.com/usepa/wntr.

Software tests
--------------------
WNTR includes automated software tests run using TravisCI at https://travis-ci.org/usepa/wntr.
Tests can also be run locally using nosetests in the WNTR directory::

	nosetests -v --with-coverage --cover-package=wntr wntr

Documentation
---------------------
WNTR includes API documentation and an online user manual at http://wntr.readthedocs.io/

Bug reports and feature requests
----------------------------------
Bug reports and feature requests can be submitted to https://github.com/usepa/wntr/issues.

Contributing
---------------------
Software developers interested in contributing to the project are encouraged to 
create a `Fork` of the project and submit a `Pull Request` using GitHub.
New code is expected to be documented using readthedocs and tested using TravisCI. 
Pull Requests will be reviewed by the maintainers of the software. 

Development team
-------------------
WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency National Homeland Security Research Center, 
Sandia National Laboratories, and Purdue University.  
The development team includes:

* Michael Bynum 
* Terra Haxton 
* Katherine Klise 
* Carl Laird 
* Dylan Moriarty 
* Regan Murray 
* Arpan Seth 

.. 
	To cite WNTR, use the following report:

	* U.S. EPA, 2016, Water Network Tool for Resilience (WNTR) User Manual, REPORT #, U.S. Environmental Protection Agency. (**NOT COMPLETE.  This will be the pdf version of the html pages**)
