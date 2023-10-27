.. raw:: latex

    \clearpage

.. _advanced_simulation:

Advanced water quality techniques
=================================
		
This section describes several advanced simulation techniques using WNTR with MSX. 



.. _msx_example1_lead:

Example 1: plumbosolvency of lead
---------------------------------

This model is described in [BWMS20]_, and represents plumbosolvency of lead in lead pipes
within a dwelling.
In this case, we will not assume that a water network model has been made for the dwelling, yet.

Model creation
~~~~~~~~~~~~~~

We create a new model, give it a name, title, and description, and we add the reference 
for the paper this model was described in.

.. doctest::

    >>> import wntr.msx
    >>> msx = wntr.msx.MultispeciesQualityModel()
    >>> msx.name = "lead_ppm"
    >>> msx.title = "Lead Plumbosolvency Model (from Burkhardt et al 2020)"
    >>> msx.desc = "Parameters for EPA HPS Simulator Model"
    >>> msx.references.append(
    ... """J. B. Burkhardt, et al. (2020) https://doi.org/10.1061/(asce)wr.1943-5452.0001304"""
    ... )
    >>> msx
    MultispeciesQualityModel(name='lead_ppm')

Next, we will update certain options.

.. doctest::

    >>> msx.options = {
    ... "report": {
    ...     "species": {"PB2": "YES"},
    ...     "species_precision": {"PB2": 5},
    ...     "nodes": "all",
    ...     "links": "all",
    ... },
    ... "timestep": 1,
    ... "area_units": "M2",
    ... "rate_units": "SEC",
    ... "rtol": 1e-08,
    ... "atol": 1e-08,
    ... }


Adding variables
~~~~~~~~~~~~~~~~
The variables that are needed for a multispecies reaction system are: species, coefficients, and terms.
These are used in expressions to define the dynamics of the reaction. All variables have at least two
attributes: their name and a note. The variable name must be a valid EPANET-MSX id, which primarily 
means no spaces are permitted. However, it may be useful to ensure that the name is a valid python 
variable name, so that it can be used to identify the variable in your code as well. The note can be
a string, a dictionary with the keys "pre" and "post", or an :class:`~wntr.epanet.util.ENcomment` object
(which has a "pre" and "post" attribute). See the ENcomment documentation for details on the meaning;
in this example we will use the string form of the note.

--------------

There is only one species defined in this model, which is dissolved lead.

========================  ===============  =================================  ========================
Name                      Type             Units                              Note
------------------------  ---------------  ---------------------------------  ------------------------
:math:`Pb`                bulk species     :math:`\mathrm{μg}_\mathrm{(Pb)}`  dissolved lead
========================  ===============  =================================  ========================

To add this species to the model, we can use the model's :meth:`~wntr.msx.multispecies.MultispeciesQualityModel.add_species`
method.
The method arguments are the name, the species_type (which can either be "bulk" or "wall"), the units,
and an optional note.
This method will add the new species to the model and also return a copy of the new species object.

.. doctest::

    >>> msx.add_species(name="PB2", species_type='bulk', units="ug", note="dissolved lead (Pb)")
    Species(name='PB2', species_type=<SpeciesType.BULK: 1>, units='ug', atol=None, rtol=None, note='dissolved lead (Pb)')

The new species can be accessed by using the item's name and indexing on the model's 
:attr:`~wntr.msx.multispecies.MultispeciesQualityModel.reaction_system` attribute.

    >>> PB2 = msx.reaction_system['PB2']
    >>> PB2
    Species(name='PB2', species_type=<SpeciesType.BULK: 1>, units='ug', atol=None, rtol=None, note='dissolved lead (Pb)')

--------------

There are two different types of coefficients that can be used in reaction expressions: constants
and parameters. Constants have a single value in every expression. Parameters have a global value
that is used by default, but which can be modified on a per-pipe or per-tank basis. This model
has two constants and one parameter.

===============  ===============  ===============  =================================  ========================
Type             Name             Value            Units                              Note
---------------  ---------------  ---------------  ---------------------------------  ------------------------
constant         :math:`M`        0.117            :math:`\mathrm{μg~m^{-2}~s^{-1}}`  desorption rate
constant         :math:`E`        140.0            :math:`\mathrm{μg~L^{-1}}`         saturation level
parameter        :math:`F`        0                `n/a`                              is pipe made of lead?
===============  ===============  ===============  =================================  ========================

We can add these to the model as follows:

.. doctest::

    >>> msx.add_constant("M", value=0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-2) * s^(-1)")
    >>> msx.add_constant("E", value=140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
    >>> msx.add_parameter("F", global_value=0, note="determines which pipes have reactions")


Adding reactions
~~~~~~~~~~~~~~~~

All species must have two reactions defined for the model to be run successfully in EPANET-MSX by WNTR.
One is a pipe reaction, the other is a tank reaction. In this case, we only have a reactions within 
pipes, so we need to set the tank reaction to be unchanging. The system of equations is:

.. math::

    \frac{d}{dt}Pb_p &= F_p \, Av_p \, M \frac{\left( E - Pb_p \right)}{E}, &\quad\text{for all pipes}~p~\text{in network}  \\
    \frac{d}{dt}Pb_t &= 0, & \quad\text{for all tanks}~t~\text{in network}

Note that the pipe reaction has a variable that we have not defined, :math:`Av`, in its expression;
this variable is a pre-defined hydraulic variable. The list of these variables can be found in 
the EPANET-MSX documentation, and also in the :attr:`~wntr.msx.base.HYDRAULIC_VARIABLES`
documentation. The reactions can be described in WNTR as

================  ==============  ==========================================================================
Reaction type     Dynamics type   Reaction expression
----------------  --------------  --------------------------------------------------------------------------
pipe              rate            :math:`F \cdot Av \cdot M \cdot \left( E - Pb \right) / E`
tank              rate            :math:`0`
================  ==============  ==========================================================================

and then added to the reaction model using the :meth:`~wntr.msx.multispecies.MultispeciesQualityModel.add_reaction`
method.

.. doctest::

    >>> msx.add_reaction("PB2", "pipe", "RATE", expression="F * Av * M * (E - PB2) / E")
    >>> msx.add_reaction(PB2, "tank", "rate", expression="0")



Example 2: arsenic oxidation and adsorption
-------------------------------------------

This example models monochloramine oxidation of arsenite/arsenate and wall
adsorption/desorption, as given in section 3 of the EPANET-MSX user manual [SRU23]_.
First, the model
will be restated here and then the code to create the model in wntr will be shown.

Model Description
~~~~~~~~~~~~~~~~~

The system of equations for the reaction in pipes is given in Eq. (2.4) through (2.7)
in [SRU23]_. This is a simplified model, taken from [GSCL94]_. 

.. math::

    \frac{d}{dt}{(\mathsf{As}^\mathrm{III})} &= -k_a ~ {(\mathsf{As}^\mathrm{III})} ~ {(\mathsf{NH_2Cl})} \\
    \frac{d}{dt}{(\mathsf{As}^\mathrm{V})}   &=  k_a ~ {(\mathsf{As}^\mathrm{III})} ~ {(\mathsf{NH_2CL})} - Av \left( k_1 \left(S_\max - {(\mathsf{As}^\mathrm{V}_s)} \right) {(\mathsf{As}^\mathrm{V})} - k_2 ~ {(\mathsf{As}^\mathrm{V}_s)} \right) \\
    \frac{d}{dt}{(\mathsf{NH_2Cl})}          &= -k_b ~ {(\mathsf{NH_2Cl})} \\
    {(\mathsf{As}^\mathrm{V}_s)}            &= \frac{k_s ~ S_\max ~ {(\mathsf{As}^\mathrm{V})}}{1 + k_s {(\mathsf{As}^\mathrm{V})}}


where the various species, coefficients, and expressions are described in the tables below.


.. list-table:: Options
    :header-rows: 1
    :widths: 3 3 10

    * - Option
      - Code
      - Description
    * - Rate units
      - "HR"
      - :math:`\mathrm{h}^{-1}`
    * - Area units
      - "M2"
      - :math:`\mathrm{m}^2`


.. list-table:: Species
    :header-rows: 1
    :widths: 2 2 2 3 4 6

    * - Name
      - Type
      - Value
      - Symbol
      - Units
      - Note
    * - AS3
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{III}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenite
    * - AS5
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{V}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenate
    * - AStot
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{tot}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenic (total)
    * - NH2CL
      - Bulk
      - "MG"
      - :math:`{\mathsf{NH_2Cl}}`
      - :math:`\mathrm{mg~L^{-1}}`
      - dissolved monochloramine
    * - AS5s
      - Wall
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{V}_{s}}`
      - :math:`\require{upgreek}\upmu\mathrm{g}~\mathrm{m}^{-2}`
      - adsorped arsenate (surface)


.. list-table:: Coefficients
    :header-rows: 1
    :widths: 2 2 2 3 4 6

    * - Name
      - Type
      - Value
      - Symbol
      - Units
      - Note
    * - Ka
      - Const
      - :math:`10`
      - :math:`k_a`
      - :math:`\mathrm{mg}^{-1}_{\left(\mathsf{NH_2Cl}\right)}~\mathrm{h}^{-1}`
      - arsenite oxidation
    * - Kb
      - Const
      - :math:`0.1`
      - :math:`k_b`
      - :math:`\mathrm{h}^{-1}`
      - chloromine decay
    * - K1
      - Const
      - :math:`5.0`
      - :math:`k_1`
      - :math:`\require{upgreek}\textrm{L}~\upmu\mathrm{g}^{-1}_{\left(\mathsf{As}^\mathrm{V}\right)}~\mathrm{h}^{-1}`
      - arsenate adsorption
    * - K2
      - Const
      - :math:`1.0`
      - :math:`k_2`
      - :math:`\textrm{L}~\mathrm{h}^{-1}`
      - arsenate desorption
    * - Smax
      - Const
      - :math:`50.0`
      - :math:`S_{\max}`
      - :math:`\require{upgreek}\upmu\mathrm{g}_{\left(\mathsf{As}^\mathrm{V}\right)}~\mathrm{m}^{-2}`
      - arsenate adsorption limit


.. list-table:: Other terms
    :header-rows: 1
    :widths: 3 3 2 3 10

    * - Name
      - Symbol
      - Expression
      - Units
      - Note
    * - Ks
      - :math:`k_s`
      - :math:`{k_1}/{k_2}`
      - :math:`\require{upgreek}\upmu\mathrm{g}^{-1}_{\left(\mathsf{As}^\mathrm{V}\right)}`
      - equilibrium adsorption coefficient 


.. list-table:: Pipe reactions
    :header-rows: 1
    :widths: 3 3 16

    * - Species
      - Type
      - Expression
    * - AS3
      - Rate 
      - :math:`-k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - AS5
      - Rate
      - :math:`k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}} -Av \left( k_1 \left(S_{\max}-{\mathsf{As}^\mathrm{V}_{s}} \right) {\mathsf{As}^\mathrm{V}} - k_2 \, {\mathsf{As}^\mathrm{V}_{s}} \right)`
    * - NH2CL
      - Rate
      - :math:`-k_b \, {\mathsf{NH_2Cl}}`
    * - AStot
      - Formula
      - :math:`{\mathsf{As}^\mathrm{III}} + {\mathsf{As}^\mathrm{V}}`
    * - AS5s
      - Equil
      - :math:`k_s \, S_{\max} \frac{{\mathsf{As}^\mathrm{V}}}{1 + k_s \, {\mathsf{As}^\mathrm{V}}} - {\mathsf{As}^\mathrm{V}_{s}}`


.. list-table:: Tank reactions
    :header-rows: 1
    :widths: 3 3 16

    * - Species
      - Type
      - Expression
    * - AS3
      - Rate
      - :math:`-k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - AS5
      - Rate
      - :math:`k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - NH2CL
      - Rate
      - :math:`-k_b \, {\mathsf{NH_2Cl}}`
    * - AStot
      - Formula
      - :math:`{\mathsf{As}^\mathrm{III}} + {\mathsf{As}^\mathrm{V}}`
    * - AS5s
      - Equil
      - :math:`0` (`not present in tanks`)


Creation in WNTR
~~~~~~~~~~~~~~~~

.. doctest::

    >>> msx = wntr.msx.MultispeciesQualityModel()
    >>> msx.name = "arsenic_chloramine"
    >>> msx.title = "Arsenic Oxidation/Adsorption Example"
    >>> msx.references.append(wntr.msx.library.cite_msx())
    >>> AS3 = msx.add_species(name="AS3", species_type="BULK", units="UG", note="Dissolved arsenite")
    >>> AS5 = msx.add_species(name="AS5", species_type="BULK", units="UG", note="Dissolved arsenate")
    >>> AStot = msx.add_species(name="AStot", species_type="BULK", units="UG", note="Total dissolved arsenic")
    >>> AS5s = msx.add_species(name="AS5s", species_type="WALL", units="UG", note="Adsorbed arsenate")
    >>> NH2CL = msx.add_species(name="NH2CL", species_type="BULK", units="MG", note="Monochloramine")
    >>> Ka = msx.add_constant("Ka", 10.0, units="1 / (MG * HR)", note="Arsenite oxidation rate coefficient")
    >>> Kb = msx.add_constant("Kb", 0.1, units="1 / HR", note="Monochloramine decay rate coefficient")
    >>> K1 = msx.add_constant("K1", 5.0, units="M^3 / (UG * HR)", note="Arsenate adsorption coefficient")
    >>> K2 = msx.add_constant("K2", 1.0, units="1 / HR", note="Arsenate desorption coefficient")
    >>> Smax = msx.add_constant("Smax", 50.0, units="UG / M^2", note="Arsenate adsorption limit")
    >>> Ks = msx.add_term(name="Ks", expression="K1/K2", note="Equil. adsorption coeff.")
    >>> _ = msx.add_reaction(
    ...     species_name="AS3", reaction_type="pipes", expression_type="rate", expression="-Ka*AS3*NH2CL", note="Arsenite oxidation"
    ... )
    >>> _ = msx.add_reaction(
    ... "AS5", "pipes", "rate", "Ka*AS3*NH2CL - Av*(K1*(Smax-AS5s)*AS5 - K2*AS5s)", note="Arsenate production less adsorption"
    ... )
    >>> _ = msx.add_reaction(
    ...     species_name="NH2CL", reaction_type="pipes", expression_type="rate", expression="-Kb*NH2CL", note="Monochloramine decay"
    ... )
    >>> _ = msx.add_reaction("AS5s", "pipe", "equil", "Ks*Smax*AS5/(1+Ks*AS5) - AS5s", note="Arsenate adsorption")
    >>> _ = msx.add_reaction(
    ...     species_name="AStot", reaction_type="pipes", expression_type="formula", expression="AS3 + AS5", note="Total arsenic"
    ... )
    >>> _ = msx.add_reaction(
    ...     species_name="AS3", reaction_type="tank", expression_type="rate", expression="-Ka*AS3*NH2CL", note="Arsenite oxidation"
    ... )
    >>> _ = msx.add_reaction(
    ...     species_name="AS5", reaction_type="tank", expression_type="rate", expression="Ka*AS3*NH2CL", note="Arsenate production"
    ... )
    >>> _ = msx.add_reaction(
    ...     species_name="NH2CL", reaction_type="tank", expression_type="rate", expression="-Kb*NH2CL", note="Monochloramine decay"
    ... )
    >>> _ = msx.add_reaction(
    ...     species_name="AStot", reaction_type="tanks", expression_type="formula", expression="AS3 + AS5", note="Total arsenic"
    ... )
    >>> msx.options.area_units = "M2"
    >>> msx.options.rate_units = "HR"
    >>> msx.options.rtol = 0.001
    >>> msx.options.atol = 0.0001


References
----------

.. [BWMS20]
    J. B. Burkhardt, et al. (2020)
    "Framework for Modeling Lead in Premise Plumbing Systems Using EPANET".
    `Journal of Water Resources Planning and Management`.
    **146** (12). https://doi.org/10.1061/(asce)wr.1943-5452.0001304. PMID:33627937.

.. [GSCL94]
    B. Gu, J. Schmitt, Z. Chen, L. Liang, and J.F. McCarthy. "Adsorption and desorption of 
    natural organic matter on iron oxide: mechanisms and models". Environ. Sci. Technol., 28:38-46, January 1994.
