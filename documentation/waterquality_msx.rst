.. raw:: latex

    \clearpage

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ...    wn.msx = wntr.msx.MsxModel('../examples/data/Net3_arsenic.msx')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')
    ...    wn.msx = wntr.msx.MsxModel('examples/data/Net3_arsenic.msx')
	
.. _msx_water_quality:

Multi-species water quality simulation
=======================================

The EpanetSimulator can use EPANET-MSX 2.0 :cite:p:`shang2023` to run 
multi-species water quality simulations.
WNTR also includes a library of MSX models, see :ref:`msx_library` for more information.
Additional multi-species simulation options are discussed in :ref:`advanced_simulation`.

A multi-species analysis is run if a :class:`~wntr.msx.model.MsxModel` is added to the 
:class:`~wntr.network.model.WaterNetworkModel`, as shown below.
In this example, the MsxModel is created from a MSX file (see :cite:p:`shang2023` for more information on file format).

.. doctest::

    >>> import wntr # doctest: +SKIP
	
    >>> wn = wntr.network.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP
    >>> wn.msx = wntr.msx.MsxModel('data/Net3_arsenic.msx') # doctest: +SKIP
    
    >>> sim = wntr.sim.EpanetSimulator(wn)
    >>> results = sim.run_sim()

The results include a quality value for each node, link, and species 
(see :ref:`simulation_results` for more details).

Multi-species model
-------------------
In addition to creating an MsxModel from a MSX file, the MsxModel 
can be built from scratch and modified using WNTR. 
For example, the user can 
add and remove species using :class:`~wntr.msx.model.MsxModel.add_species` and :class:`~wntr.msx.model.MsxModel.remove_species`, or 
add and remove reactions using :class:`~wntr.msx.model.MsxModel.add_reaction` and :class:`~wntr.msx.model.MsxModel.remove_reaction`.
See the API documentation for the :class:`~wntr.msx.model.MsxModel` for a complete list of methods.

Variables
~~~~~~~~~
Variables include **species**, **coefficients**, and **terms**.
These are used in **expressions** to define the dynamics of the reaction. All variables have at least two
attributes: a name and a note. 
The variable name must be a valid EPANET-MSX id, which primarily 
means no spaces are permitted. However, it may be useful to ensure that the name is a valid python 
variable name, so that it can be used to identify the variable in your code as well. 
The note can be a string, a dictionary with the keys "pre" and "post", or an :class:`~wntr.epanet.util.ENcomment` object
(which has a "pre" and "post" attribute). See the ENcomment documentation for details on the meaning;
in this example the string form of the note is used.

There are two different types of coefficients that can be used in reaction expressions: **constants**
and **parameters**. Constants have a single value in every expression. Parameters have a global value
that is used by default, but which can be modified on a per-pipe or per-tank basis. 

Pre-defined hydraulic variables can be found in 
the EPANET-MSX documentation, and are also defined in WNTR as :attr:`~wntr.msx.base.HYDRAULIC_VARIABLES`.

Reactions
~~~~~~~~~
All species must have two reactions defined for the model to be run successfully in EPANET-MSX by WNTR.
One is a **pipe reaction**, the other is a **tank reaction**. 

Examples that illustrate how to build MSX models in WNTR are included in :ref:`advanced_simulation`.
