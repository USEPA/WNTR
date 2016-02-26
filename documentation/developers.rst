Developers
==========

WNTR is hosted on github at the Open Water Analytics site, https://github.com/OpenWaterAnalytics/WNTR.
Bug reports can be submitted to https://github.com/OpenWaterAnalytics/WNTR/issues.

WNTR includes automated tests run using nosetests.  Test are
run nightly using the Jenkins continuous build and test server 
at Sandia National Laboratories. 
Tests can be run locally using nosetests in the WNTR directory::

	nosetests -v --with-coverage --cover-package=wntr wntr

.. http://jenkins.sandia.gov/view/TEVA/job/resilience_trunk_python2.7

WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency National Homeland Security Research Center, 
Sandia National Laboratories, and Purdue University.  
The development team includes:

* Michael Bynum (Purdue)
* Terra Haxton (EPA)
* Katherine Klise (SNL)
* Carl Laird (Purdue)
* Dylan Moriarty (SNL)
* Regan Murray (EPA)
* Arpan Seth (Purdue)

To cite WNTR, use the following report:

* U.S. EPA, 2016, Water Network Tool for Resilience (WNTR) User Manual, REPORT #, U.S. Environmental Protection Agency. (**NOT COMPLETE.  This will be the pdf version of the html pages**)
