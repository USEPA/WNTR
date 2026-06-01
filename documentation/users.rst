.. raw:: latex

    \clearpage

.. _users:

User community	
================================

WNTR has an active user community, which includes water utilities, universities, and government agencies. 
This page is intended to highlight contributors and collaborators, along with software and publications that use WNTR.
The page also includes publications from the core development team.

.. note:: 
   This page will be updated periodically. If you have content that you would like 
   to add to this page, email the contacts listed on the WNTR GitHub webpage (https://github.com/USEPA/WNTR) 
   or submit a pull request with the update.

Contributors
-------------

WNTR welcomes software contributions from the community! 
See the `WNTR Contributors <https://github.com/USEPA/WNTR/graphs/contributors?all=1>`_ page for a complete list of people that have contributed code and documentation to WNTR.
Many people have also contributed to WNTR by posting issues and feature requests on the `WNTR Issues <https://github.com/USEPA/WNTR/issues>`_ page.  

Collaborators
--------------
The following institutions have partnered with the EPA and Sandia on the development and application of WNTR.

.. list-table::
   :widths: 50 50
   :header-rows: 0
   
   * - Arcadis
     - Pittsburgh Water and Sewer Authority
   * - Arizona State University
     - Puerto Rico Aqueduct and Sewer Authority
   * - Delft University of Technology
     - Purdue University
   * - Global Quality Corp
     - Stanford University
   * - Greater Cincinnati Water Works
     - Town of Poughkeepsie
   * - MIT Lincoln Laboratory 
     - University of Texas at Austin
   * - Naval Postgraduate School
     - U.S. Army Corps of Engineers, Engineer Research and Development Center
   * - Oregon State University
     - U.S. Virgin Islands Water and Power Authority

Additional funding for WNTR has been provided by the 
Department of Energy (DOE), 
Environmental Security Technology Certification Program (ESTCP), and 
Sandia's Laboratory Directed Research and Development (LDRD) program.

Software
--------

WNTR is used within several externally developed software packages, which further extend capabilities for water distribution systems analysis.
The following list includes software packages that use WNTR. 
See the `WNTR GitHub Dependency Graph <https://github.com/USEPA/WNTR/network/dependents?dependent_type=REPOSITORY>`_ 
to find additional repositories and packages that use WNTR.

.. include:: third_party_software.rst

Publications
------------

WNTR has been used in numerous publications to analyze water distribution systems.  
The following publications include journal articles, conference papers, 
Master's Theses, and PhD Dissertations that use WNTR.  

.. note:: 
   Citations were pulled from Google Scholar in BibTeX format and may contain inaccurate or missing content, or do not render correctly.

.. dropdown:: **Publications that use WNTR**
	
    Citations listed in alphabetical order.
	
    .. bibliography:: bibtex/wntr_use.bib
        :all:
        :list: enumerated

Development Team
------------------

EPA and Sandia started collaborating on research related to water security in 2003, 
with a Sandia funded LDRD project
focused on computational methods to detect chem-bio attacks. 
The collaboration has since been funded under an Interagency Agreement between EPA and Sandia.
Several open-source software packages have been developed by the team, including:

* Canary: https://github.com/USEPA/CANARY
* Water Security Toolkit (WST): https://github.com/USEPA/Water-Security-Toolkit
* Water Network Tool for Resilience (WNTR): https://github.com/USEPA/WNTR

The following publications were published as part of the EPA/Sandia Interagency Agreement 
or related projects.

.. dropdown:: **EPA/Sandia Publications**

    Citations listed in reverse chronological order.
	
    .. bibliography:: bibtex/wntr_team.bib
        :all:
        :style: unsrt
        :list: enumerated
