Source code
===============

Testing
-----------

WNTR includes automated tests run using nosetests.  Test are
run nightly using the Jenkins continuous build and test server 
at Sandia National Laboratories. 

.. http://jenkins.sandia.gov/view/TEVA/job/resilience_trunk_python2.7

Tests can be run locally using nosetests in the WNTR directory::

	nosetests -v --with-coverage --cover-package=wntr wntr

Bug reports
-----------

Bug reports can be submitted to the WNTR trac site at 
https://software.sandia.gov/trac/resilience

Code documentation
------------------

.. toctree::
   :maxdepth: 2

   network
   simulation
   metrics
   pyepanet
   units
