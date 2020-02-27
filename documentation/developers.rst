.. raw:: latex

    \clearpage
	
.. _developers:

Software quality assurance
=======================================

The following section includes information about 
the WNTR software repository, 
software tests,
documentation, 
examples, 
bug reports,
feature requests, and
ways to contribute.

GitHub repository
---------------------
WNTR is maintained in a version controlled repository.  
WNTR is hosted on US EPA GitHub organization at https://github.com/USEPA/WNTR.

Software tests
--------------------
WNTR includes continuous integration software tests that are run using Travis CI.  
The tests are run each time changes are made to the repository.  
The tests cover a wide range of unit and 
integration tests designed to ensure that the code is performing as expected.  
New tests are developed each time new functionality is added to the code.   
Testing status (passing/failed) and code coverage statistics are posted on 
the README section at https://github.com/USEPA/WNTR.
	
Tests can also be run locally using the Python package nose.  
For more information on nose, see  http://nose.readthedocs.io/.
The nose package comes with a command line software tool called nosetests.
Tests can be run in the WNTR directory using the following command::

	nosetests -v --with-coverage --cover-package=wntr wntr

In addition to the publicly available software tests run using Travis CI,
WNTR is also tested on private servers using several large water utility network models.
	
Documentation
---------------------
WNTR includes a user manual that is built using the Read the Docs service.
The user manual is automatically rebuilt each time changes are made to the code.
The documentation is publicly available at http://wntr.readthedocs.io/.
The user manual includes an overview, installation instructions, simple examples, 
and information on the code structure and functions.  
WNTR includes documentation on the API for all 
public functions, methods, and classes.
New content is marked `Draft`.

Examples
---------------------
WNTR includes examples to help new users get started.  
These examples are intended to demonstrate high level features and use cases for WNTR.  
The examples are tested to ensure they stay current with the software project.

Bug reports and feature requests
----------------------------------
Bug reports and feature requests can be submitted to https://github.com/USEPA/WNTR/issues.  
The core development team will prioritize and assign bug reports and feature requests to team members.

Contributing
---------------------
Software developers, within the core development team and external collaborators, 
are expected to follow standard practices to document and test new code.  
Software developers interested in contributing to the project are encouraged to 
create a `Fork` of the project and submit a `Pull Request` using GitHub.  
Pull requests will be reviewed by the core development team.  

Pull requests must meet the following minimum requirements to be included in WNTR:

* Code is expected to be documented using Read the Docs.  

* Code is expected to be sufficiently tested using Travis CI.  `Sufficient` is judged by the strength of the test and code coverage.  80% code coverage is recommended.  

* Large files (> 1Mb) will not be committed to the repository without prior approval.

* Network model files will not be duplicated in the repository.  Network files are stored in examples/network and wntr/tests/networks_for_testing only.

.. note:: 
  The USEPA/WNTR GitHub site, https://github.com/USEPA/WNTR, does not link to Travis CI for continuous integration software testing.  
  The core development team uses the sandialabs/WNTR fork, https://github.com/sandialabs/wntr, to run tests.
  To submit a Pull Request to USEPA/WNTR, the developer needs to link their fork to Travis so that test results can be inspected.
  If the developer does not have Travis linked to their fork, the Pull Request can be submitted to the sandialabs/WNTR fork.
  All bug reports and feature requests should be submitted to USEPA/WNTR.

Development team
-------------------
WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency Office of Research and Development, 
Sandia National Laboratories, and Purdue University.  
See https://github.com/USEPA/WNTR/graphs/contributors for a full list of contributors.