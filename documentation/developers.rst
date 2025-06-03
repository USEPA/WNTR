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
Developers should follow the :ref:`developer_instructions` to 
clone and setup WNTR.

GitHub repository
---------------------
WNTR is maintained in a version controlled repository.  
WNTR is hosted on US EPA GitHub organization at https://github.com/USEPA/WNTR.

.. _software_tests:

Software tests
--------------------
WNTR includes continuous integration software tests that are run using GitHub Actions.
Travis CI and AppVeyor are used by the core development team as secondary testing services.
The tests are run each time changes are made to the repository.  
The tests cover a wide range of unit and 
integration tests designed to ensure that the code is performing as expected.  
New tests are developed each time new functionality is added to the code.   
Testing status (passed/failed) and code coverage statistics are posted on 
the README section at https://github.com/USEPA/WNTR.
	
Tests can also be run locally using the Python package pytest.  
For more information on pytest, see  https://docs.pytest.org/.
The pytest package comes with a command line software tool.
Tests can be run in the WNTR directory using the following command in a command line/PowerShell prompt::

	pytest wntr

In addition to the publicly available software tests run using GitHub Actions,
WNTR is also tested on private servers using several large water utility network models.
	
Documentation
---------------------
WNTR includes a user manual that is built using GitHub Actions.
The user manual is automatically rebuilt each time changes are made to the code.
The documentation is publicly available at https://usepa.github.io/WNTR/.
The user manual includes an overview, installation instructions, simple examples, 
and information on the code structure and functions.  
WNTR includes documentation on the API for all 
public functions, methods, and classes using NumPy Style Python Docstrings.
New content is marked `Draft`.
Python documentation string formatting can be found at
https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html

* To build HTML files of the documentation locally, run the following command in a 
  command line/PowerShell prompt from the documentation directory::

	  make html

  HTML files are created in the ``documentation/_build/html`` directory.
  Open ``index.html`` to view the HTML documentation in a browser.

* To build Latex files of the documentation locally, run the following command in a 
  command line/PowerShell prompt from the documentation directory::

	  make latex

  Latex files are created in the ``documentation/_build/latex`` directory.
  Copy all the files into Overleaf and build wntr.tex to create a PDF.

* To run the doctests locally, run the following command in a 
  command line/PowerShell prompt from the documentation directory::
  
	  pytest --doctest-glob="*.rst" .

  Note that this also creates graphics used in the documentation.

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

Pull requests can be made to the **main** or **dev** (development) branch.  
Developers can discuss new features and the appropriate branch for contributing 
by opening a new issue on https://github.com/USEPA/WNTR/issues.  

Pull requests must meet the following minimum requirements to be included in WNTR:

* Code is expected to be documented using NumPy Style Python Docstrings.

* Code is expected have sufficient tests.  `Sufficient` is judged by the strength of the test and code coverage. An 80% code coverage is recommended.  

* Large files (> 1Mb) will not be committed to the repository without prior approval.

* Network model files will not be duplicated in the repository.  Network files are stored in examples/network and wntr/tests/networks_for_testing only.

Software release
------------------
The software release process requires administrative privileges and knowledge about the external services used in the release process.
The release creates wheels that are available on PyPI and conda-forge.
A release candidate (with version number rc1, rc2, ...) should be created prior to an official release.
Changes to WNTR (Steps 1, 2, and 12) can be completed using pull requests, or through direct edits on GitHub.
Since the release depends on external services, the instructions below often need slight modification between release cycles.

1. **Check the version number**: The version number is defined in WNTR/wntr/__init__.py.  
   The version number is denoted <version> in the instructions below and is in X.Y.Z format, where X is the major release number, 
   Y is the minor release number, and Z is a bug fix release number.  
   
   If creating a release candidate, include rc1, rc2, etc at the end of the version number.

2. **Check or create release notes**: The release notes are in WNTR/documentation/whatsnew/<version>.rst 
   (see Step 3 to autogenerate release notes) and make sure the 
   <version>.rst file is included in WNTR\documentation\whatsnew.rst.
   Update the release date in <version>.rst.
  
3. **Create a new release on GitHub**: Go to https://github.com/USEPA/WNTR/releases and select “Draft a new release”.
   Create a new tag (named <version>) and title (“Version <version> Release”).
   Autogenerate release notes by selecting “Generate release notes”, clean up the text to have consistent language.  
   The same text can go in <version>.rst.  
   
   If this is a release candidate, select "Set as a pre-release", otherwise select "Set as the latest release". 
   Select "Publish release".  

4. **Push wheels to PyPI**: The new release will initiate GitHub Actions to run workflows, 
   this includes a step to push wheels to PyPI.
   
   If the wheels are not pushed to PyPI (because of the PyPI token or some other reason), 
   download the artifact from the release (the file is named wntr-<version>.zip), unzip the file and use https://github.com/pypa/twine 
   to upload the files to PyPI. See instructions at https://twine.readthedocs.io/.

5. **Create a personal fork of the conda-forge wntr-feedstock**: 
   The conda-forge wntr-feedstock is located at https://github.com/conda-forge/wntr-feedstock.
   The personal fork will be named https://github.com/<username>/wntr-feedstock, 
   where <username> is your github username.

6. **Clone the wntr-feedstock and create a new branch**: Clone your personal fork of the wntr-feedstock and checkout a new branch.
   For examples, the <branchname> could be named "release-<version>".  The following commands clone wntr-feedstock and create a branch::
		
      git clone https://github.com/<username>/wntr-feedstock.git
      cd wntr-feedstock
      git checkout –b <branchname>

7. **Update the feedstock recipe**: The feedstock recipe is stored in wntr-feedstock/recipe/meta.yaml.
   The following steps are needed to update the file.

   a. Update the version number in ``{% set version = <version> %}``
   
   b. Update the source url to point to correct version in ``url: https://github.com/USEPA/WNTR/archive/<version>.zip``
   
   c. Update the SHA256 key in ``sha256: 78aa135219...``. 
      Generate the SHA256 key for the source code archive using openssl. 
      More info can be found at http://conda-forge.org/docs/maintainer/adding_pkgs.html or in the example 
      recipe at https://github.com/conda-forge/staged-recipes/blob/master/recipes/example/meta.yaml.

      Download the zip by copying and pasting the following address into a browser window::

	     https://github.com/USEPA/WNTR/archive/<version>.zip
		 
      You should now have a downloaded file named WNTR-<version>.zip. 
      Generate the SHA256 key by running the following command, in the same folder as the file::

	     openssl sha256 WNTR-<version>.zip

      Copy the resulting SHA256 key and paste it on the sha256 line.
	  
   d. Reset the build number to 0 in ``number: 0``. The build number only needs to be increased if a new build is needed for the same source version. 
      See https://github.com/conda-forge/staged-recipes/wiki/Frequently-asked-questions. 
   
   e. Ensure requirements are correct.  Use pin compatibility to specify specific versions, for example::

	    {{ pin_compatible('geopandas', upper_bound='1.0') }}
	
   f. Commit changes to meta.yml::
   
	     git commit -m "update meta.yaml" recipe/meta.yaml
	  
   g. Push changes to your fork/branch::

	     git push <username> <branchname>

8. **Render the feedstock recipe on conda-forge**: Create a pull request to https://github.com/conda-forge/wntr-feedstock. Review the checklist, 
   and have the conda-forge-admin rerender the files by adding ``@conda-forge-admin, please rerender`` to the pull request.  
   Once all tests have passed, merge the pull request. The pull request description should include the following checks and message for the conda-forge-admin:: 

	   * [x] Used a personal fork of the feedstock to propose changes
	   * [x] Bumped the build number (if the version is unchanged)
	   * [x] Reset the build number to 0 (if the version changed)
	   * [ ] Re-rendered with the latest conda-smithy 
	   * [x] Ensured the license file is being packaged.
	   @conda-forge-admin, please rerender

9. **Test the release (or release candidate)**: Create a new conda environment with a WNTR supported version of Python and no default packages, 
   and then install WNTR and then print the version number (pytest can also be run locally to further test the release).
   To test the PyPI installation::
    
	   conda create --name test1 python=3.12 --no-default-packages
	   conda activate test1
	   pip install wntr
	   python -c "import wntr; print(wntr.__version__)"
    
   To test the conda installation::
    
	   conda create --name test2 python=3.12 --no-default-packages
	   conda activate test2
	   conda install -c conda-forge wntr
	   python -c "import wntr; print(wntr.__version__)"

10. **Add an announcement to the homepage**: If this is not a release candidate, update attention.rst with an 
    announcement for the new release (update version number).  This will update https://usepa.github.io/WNTR.

Development team
-------------------
WNTR was developed as part of a collaboration between the United States 
Environmental Protection Agency Office of Research and Development and
Sandia National Laboratories.  
See https://github.com/USEPA/WNTR/graphs/contributors for a full list of contributors.
