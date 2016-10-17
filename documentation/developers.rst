.. _developers:

Software Quality Assurance
=======================================

The following section includes information about 
the WNTR software repository, 
software tests and documentation, and 
ways to contribute and request new features.

GitHub repository
---------------------
WNTR is maintained in a version controlled repository.  
WNTR is hosted on USEPA GitHub organization at https://github.com/usepa/wntr.

Software tests
--------------------
WNTR includes continuous integration software tests that are run each time 
changes are made to the repository.  The tests cover a wide range of unit and 
integration tests designed to ensure that the code is performing as expected.  
New tests are developed each time new functionality is added to the code.   
Testing results are publicly available at https://travis-ci.org/usepa/wntr.  
Testing status (passing/failed) and code coverage statistics are posted on 
the README section at https://github.com/usepa/wntr.
	
Tests can also be run locally using nosetests in the WNTR directory using the following command::

	nosetests -v --with-coverage --cover-package=wntr wntr

Documentation
---------------------
WNTR includes a user manual that is built using Read the Docs.
Using this service, the user manual is rebuilt each time changes are made to the code.
The documentation is publicly available at http://wntr.readthedocs.io/ 
The user manual includes an overview, installation instructions, simple examples, 
and information on the code structure and functions.  
WNTR includes documentation on the application program interface (API) for all 
public functions, methods, and classes.
New content is marked `Draft`.

Examples
---------------------
WNTR includes examples to help get new users started.  
These examples are intended to demonstrate high level features and use cases for WNTR.  
The examples are tested to ensure they stay current with the software project.

Bug reports and feature requests
----------------------------------
Bug reports and feature requests can be submitted to https://github.com/usepa/wntr/issues.  
The core development team will prioritize and assign bug reports and feature requests to team members.

Contributing
---------------------
Software developers, within the core development team or external collaborators, 
are expected to follow standard practices to document and test new code.  
Software developers interested in contributing to the project are encouraged to 
create a `Fork` of the project and submit a `Pull Request` using GitHub.  
Pull requests will be reviewed by the core development team.  

Pull requests must meet the following minimum requirements to be included in WNTR:

* Code is expected to be documented using Read the Docs.  

* Code is expected to be sufficiently tested using Travis CI.  `Sufficient` is judged by the strength of the test and code coverage.  80% code coverage is recommended.  

* Large files (> 1Mb) will not be committed to the repository without prior approval.

* Network model files will not be duplicated in the repository.  Network files are stored in examples/network and wntr/tests/networks_for_testing only.

Development team
-------------------
WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency National Homeland Security Research Center, 
Sandia National Laboratories, and Purdue University.  

See https://github.com/USEPA/WNTR/graphs/contributors for a list of contributors.