Developers
==========

WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency National Homeland Security Research Center, 
Sandia National Laboratories, and Purdue University.  
The development team includes:

* Regan Murray (EPA)
* Terra Haxton (EPA)
* Katherine Klise (SNL)
* Dylan Moriarty (SNL)
* Michael Bynum (Purdue)
* Arpan Seth (Purdue)
* Carl Laird (Purdue)

To cite WNTR, use the following report:

* U.S. EPA, 2016, Water Network Tool for Resilience (WNTR) User Manual, REPORT #, U.S. Environmental Protection Agency. (**NOT COMPLETE.  This will be the pdf version of the html pages**)

Github
------

(**NOT COMPLETE.  This section will be updated to include information about github, bug reports, and testing**)

Bug reports
^^^^^^^^^^^
Bug reports can be submitted to the WNTR trac site at 
https://software.sandia.gov/trac/resilience

Testing
^^^^^^^^^^^
WNTR includes automated tests run using nosetests.  Test are
run nightly using the Jenkins continuous build and test server 
at Sandia National Laboratories. 

.. http://jenkins.sandia.gov/view/TEVA/job/resilience_trunk_python2.7

Tests can be run locally using nosetests in the WNTR directory::

	nosetests -v --with-coverage --cover-package=wntr wntr

