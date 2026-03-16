.. raw:: latex

    \clearpage
	
.. _extensions:

Extensions
==========
|extensions|

.. |extensions| image:: https://github.com/kaklise/WNTR/actions/workflows/extensions.yml/badge.svg
   :target: https://github.com/kaklise/WNTR/actions/workflows/extensions.yml
   
WNTR extensions are intended to house beta and self-contained functionality that adds to WNTR, 
but is currently not part of core WNTR development.  The extensions should be designed for a wide audience.

WNTR currently includes the following extension:

- :ref:`hello_world`

Additional extensions will be added at a later date.

.. note:: 
   Developers interested in contributing to WNTR extensions should communicate with the core development team
   through https://github.com/USEPA/WNTR/issues prior to submitting a pull request.
   See :ref:`contributing` for more information.
   
   While documentation is required for extensions, the documentation is not included in the 
   `WNTR EPA Report <https://cfpub.epa.gov/si/si_public_record_report.cfm?Lab=NHSRC&dirEntryID=337793>`_.  
   Documentation for extensions is only available online. 
   Extensions that have long term test failures will be removed from the repository.

Third-party packages
---------------------
Developers are also encouraged to create third-party software packages that extends functionality in WNTR.  
A list of software packages that build on WNTR is included below:

.. include:: third_party_software.rst
