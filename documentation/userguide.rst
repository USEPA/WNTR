.. figure:: _static/logo.jpg
   :scale: 10 %
   :alt: Logo

User Guide
==========

The Water Network Tool for Resilience (WNTR) is an EPANET compatible Python package 
designed to simulate and analyze resilience of water distribution networks.

US EPA Disclaimer
-----------------

The U.S. Environmental Protection Agency through its Office of Research and Development funded and collaborated 
in the research described here under an Interagency Agreement with the Department of Energy's Sandia National Laboratories.
It has been subjected to the Agency's review and has been approved for publication. Note that approval does not signify that 
the contents necessarily reflect the views of the Agency. Mention of trade names products, or services does not convey official 
EPA approval, endorsement, or recommendation.  


Sandia Funding Statement
------------------------

Sandia National Laboratories is a multimission laboratory managed and operated by National Technology and 
Engineering Solutions of Sandia, LLC., a wholly owned subsidiary of Honeywell International, Inc., for the 
U.S. Department of Energy's National Nuclear Security Administration under contract DE-NA-0003525.

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Introduction

   overview
   installation
   framework
   units
   getting_started

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Model building

   waternetworkmodel
   model_io
   controls
   networkxgraph
   layers
   options

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Simulation

   hydraulics
   waterquality
   resultsobject

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Analysis

   disaster_models
   criticality
   resilience
   fragility
   morph
   graphics
   gis
   advancedsim
   errors

.. toctree::
    :maxdepth: 1
    :hidden:
    :caption: Backmatter

    license
    whatsnew
    developers
    acronyms
    reference


Citing WNTR
-----------------
To cite WNTR, use one of the following references:

* Klise, K.A., Hart, D.B., Bynum, M., Hogge, J., Haxton, T., Murray, R., Burkhardt, J. (2020). Water Network Tool for Resilience (WNTR) User Manual: Version 0.2.3. U.S. EPA Office of Research and Development, Washington, DC, EPA/600/R-20/185, 82p.

* Klise, K.A., Murray, R., Haxton, T. (2018). An overview of the Water Network Tool for Resilience (WNTR), In Proceedings of the 1st International WDSA/CCWI Joint Conference, Kingston, Ontario, Canada, July 23-25, 075, 8p.

* Klise, K.A., Bynum, M., Moriarty, D., Murray, R. (2017). A software framework for assessing the resilience of drinking water systems to disasters with an example earthquake case study, Environmental Modelling and Software, 95, 420-431, doi: 10.1016/j.envsoft.2017.06.022
