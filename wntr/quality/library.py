# -*- coding: utf-8 -*-
# @Contributors:
#   Jonathan Burkhardt, U.S. Environmental Protection Agency, Office of Research and Development

r"""A library of common multispecies reactions.

Values in libarary are currently for test purposes only. These highlight the 
reaction form/relationships but do not provide the specific system kinetics. 
In all cases, updates will be necessary to use a specific model with a specific
network; that is, sources, pipes, nodes are for a given network, and must be 
updated for different water network models. Citations are provided for the 
reaction values and models.

Notes
-----
.. important::

    The docstrings you will write will likely use mathematics, as with the 
    models already provided. You will need to make them "raw" strings - e.g., 
    ``r'''docstring'''``. This is because most LaTeX commands will use ``\`` 
    characters in the commands, which can mess up documentation unless the docstrings 
    are specified as raw, not interpreted, text.

.. important::

    Make sure to provide all appropriate references to the model in your creation 
    function.

.. _msx_library_note:

.. rubric:: Note regarding functions within the library that accept a water network model

If a water network is provided that does not have an ``msx`` attribute, then a new model will be
created and added to the network. The new model will also be returned as an object.

If a water network is provided that already has an ``msx`` attribute, then this function will:
first check to see if there are variables that are in conflict with the existing reaction
model. If there are conflicts, an exception will be raised. The :attr:`~MultispeciesOptions.area_units`
and :attr:`~MultispeciesOptions.rate_units` will also be checked for conflicts, and an exception raised
if they differ from the already-existing units.
If there are no conflicts, then the variables and reactions for this model will be added to the
existing model. If there are conflicts, then the user must resolve them and try again.

"""

import logging

from wntr.quality.multispecies import MultispeciesQualityModel
from wntr.network.model import WaterNetworkModel
from .multispecies import MultispeciesQualityModel
from .base import LocationType, SpeciesType, DynamicsType

PIPE = LocationType.PIPE
TANK = LocationType.TANK
BULK = SpeciesType.BULK
WALL = SpeciesType.WALL
RATE = DynamicsType.RATE
EQUIL = DynamicsType.EQUIL
FORMULA = DynamicsType.FORMULA

logger = logging.getLogger(__name__)

__all__ = [
    "cite_msx",
    "nicotine",
    "nicotine_ri",
    "lead_ppm",
    "arsenic_chloramine",
    "batch_chloramine_decay",
]

##########################################
##
##  IMPORTANT NOTE FOR CONTRIBUTORS
##
## The docstrings you write will likely use mathematics, as with the models already provided.
## you will need to make them "raw" strings -- i.e.,   r"""adocstring"""
## This is because most latex/mathjax formats use \ characters, which mess up docscrape
## unless you mark the string as raw, not interpreted, text.
##


def cite_msx() -> dict:
    """A citation generator for the EPANET-MSX user guide.

    References
    ----------
    [SRU23]_ Shang, F. and Rossman, L.A. and Uber, J.G. (2023) "EPANET-MSX 2.0 User Manual". (Cincinnati, OH: Water Infrastructure Division (CESER), U.S. Environmental Protection Agency). EPA/600/R-22/199.

    """
    return 'Shang, F. and Rossman, L.A. and Uber, J.G. (2023) "EPANET-MSX 2.0 User Manual". (Cincinnati, OH: Water Infrastructure Division (CESER), U.S. Environmental Protection Agency). EPA/600/R-22/199.'
    # return dict(
    #     entry_type="report",
    #     key="SRU23",
    #     fields=dict(
    #         title="EPANET-MSX 2.0 User Manual",
    #         year=2023,
    #         author="Shang, F. and Rossman, L.A. and Uber, J.G.",
    #         institution="Water Infrastructure Division (CESER), U.S. Environmental Protection Agency",
    #         location="Cincinnati, OH",
    #         number="EPA/600/R-22/199",
    #     ),
    # )


# FIXME:  Need to actually do the checks and adding to the wn


# ===================== Nicotine-chlorine model
#
def nicotine(wn: WaterNetworkModel = None) -> MultispeciesQualityModel:
    r"""Create a new nicotine-chlorine reaction model, and optionally attach it to a water network model.

    Parameters
    ----------
    wn : WaterNetworkModel, optional
        the water network to use to hold the new or updated reaction model, by default None

    Returns
    -------
    MultispeciesQualityModel
        the new or updated reaction/quality model

    Model Description
    -----------------
    This model defines a simple nicotine-chlorine reaction. The model only defines bulk species
    and does not specify any tank reactions. There is no reactive intermediate species in this
    implementation, see :func:`nicotine_ri` for a model with a reactive intermediary.

    Bulk species
        .. math::

            Nx &:= \mathrm{mg}_\mathrm{(Nic)}~\text{[nicotine]} \\
            HOCL &:= \mathrm{mg}_\mathrm{(Cl)}~\text{[chlorine]}

    Coefficients
        .. math::

            k_d &= 2.33 \times 10^{-3}~\mathrm{min}^{-1} \\
            k_1 &= 5.92 \times 10^{-2}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Nic)}}^{-1} \\
            k_2 &= 1.83 \times 10^{-1}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Cl)}}^{-1}

    Other terms
        .. math::

            RxCl &= k_d \, HOCL + k_1 \, Nx \, HOCL \\
            RxN &= k_2 \, Nx \, HOCL

    Pipe reactions
        .. math::

            \frac{d}{dt}Nx &= -RxN \\
            \frac{d}{dt}HOCL &= -RxCl

    The tank reactions are not explicitly defined in this model.


    Notes
    -----
    Please see `msx_library_note`_ for information on how a model that is passed in should be handled.

    """
    msx = MultispeciesQualityModel()
    msx.name = "nicotine"
    msx.title = ("Nicotine - Chlorine reaction",)
    msx.options.area_units = "m2"
    msx.options.rate_units = "min"
    msx.options.timestep = 1
    msx.add_species("Nx", "bulk", units="mg", note="Nicotine")
    msx.add_species(name="HOCL", species_type=BULK, units="mg", note="Free chlorine")
    msx.add_constant("kd", value=2.33e-3, units="min^(-1)", note="decay rate")
    msx.add_constant(
        "K1",
        value=5.92e-2,
        units="L * min^(-1) * mg^(-1)",
        note="decay constant for chlorine as function of mass(Nic)",
    )
    msx.add_constant(
        "K2",
        value=1.84e-1,
        units="L * min^(-1) * mg^(-1)",
        note="decay constant for nicotine as function of mass(Cl)",
    )
    msx.add_term("RxCl", expression="kd * HOCL + K1 * Nx * HOCL")
    msx.add_term("RxN", expression="K2 * Nx * HOCL")
    msx.add_reaction(species="Nx", location="pipe", dynamics_type="rate", expression="-RxN")
    msx.add_reaction("HOCL", PIPE, dynamics_type=RATE, expression="-RxCl")
    return msx


# ===================== Nicotine-chlorine reactive intermediate species
#
def nicotine_ri(wn: WaterNetworkModel = None) -> MultispeciesQualityModel:
    r"""A nicotine-chlorine reaction with a reactive intermediate.
    
    Parameters
    ----------
    wn : WaterNetworkModel, optional
        the water network to use to hold the new or updated reaction model, by default None

    Returns
    -------
    MultispeciesQualityModel
        the new or updated reaction/quality model

    Model Description
    -----------------
    This model defines a simple nicotine-chlorine reaction with a reactive intermediate species. 
    The model only defines bulk species, and the pipe and tank reactions use the same expressions.
    For a simpler model, see :func:`nicotine`.    

    Bulk species
        .. math::
            Nx &:= \mathrm{mg}_\mathrm{(Nic)}~\text{[nicotine]} \\
            HOCL &:= \mathrm{mg}_\mathrm{(Cl)}~\text{[chlorine]} \\
            NX2 &:= \mathrm{mg}_\mathrm{(Nic_2)}~\text{[reaction~intermediary]}

    Coefficients
        .. math::
            k_d &= 3.0 \times 10^{-5}~\mathrm{min}^{-1} \\
            k_1 &= 9.75 \times 10^{-2}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Nic)}}^{-1}\\
            k_2 &= 5.73 \times 10^{-1}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Cl)}}^{-1}\\
            K_3 &= 1.34 \times 10^{-2}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Nic_2)}}^{-1}\\
            K_4 &= 2.19 \times 10^{-2}~\mathrm{L}\,\mathrm{min}^{-1}\,\mathrm{mg}_{\mathrm{(Cl)}}^{-1}

    Other terms
        .. math:: 
            RXCL &= k_d \, HOCL + k_1 \, Nx \, HOCL + K_3 \, NX2 \, HOCL\\
            RXN &= k_2 \, Nx \, HOCL\\
            RXNX2 &= k_2 \, Nx \, HOCL - K_4 \, NX2 \, HOCL

    Pipe reactions and tank reactions *(defined separately for pipe and tank)*
        .. math::
            \frac{d}{dt}Nx &= -RXN\\
            \frac{d}{dt}HOCL &= -RXCL\\
            \frac{d}{dt}HOCL &= RXNX2

    Notes
    -----
    If a water network is provided that does not have an ``msx`` attribute, then a new model will be
    created and added to the network. The new model will also be returned as an object.
    
    If a water network is provided that already has an ``msx`` attribute, then this function will:
    first check to see if there are variables that are in conflict with the existing reaction
    model. If there are conflicts, an exception will be raised. The :attr:`~MultispeciesOptions.area_units`
    and :attr:`~MultispeciesOptions.rate_units` will also be checked for conflicts, and an exception raised
    if they differ.
    If there are no conflicts, then the variables and reactions for this model will be added to the
    existing model. If there are conflicts, then the user must resolve them and try again.
    """
    msx = MultispeciesQualityModel()
    msx.name = "nicotine_ri"
    msx.title = ("Nicotine - Chlorine reaction with reactive intermediate",)

    # Set the options
    msx.options.area_units = "m2"
    msx.options.rate_units = "min"
    msx.options.timestep = 1
    msx.options.atol = 1.0e-10
    msx.options.rtol = 1.0e-10

    # Add species
    msx.add_species("Nx", "bulk", units="mg", note="Nicotine")
    msx.add_species("HOCL", BULK, units="mg", note="Free Chlorine")
    msx.add_species("NX2", "b", units="mg", note="Intermediate Nicotine Reactive")

    # Add coefficients
    msx.add_constant("kd", 3.0e-5, units="1/min", note="decay constant for chlorine over time")
    msx.add_constant(
        "K1", 9.75e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)"
    )
    msx.add_constant("K2", 5.73e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    msx.add_constant(
        "K3", 1.34e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Nic2)"
    )
    msx.add_constant("K4", 2.19e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")

    # Add terms (named subexpressions)
    msx.add_term("RXCL", "kd * HOCL + K1 * Nx * HOCL + K3 * NX2 * HOCL")
    msx.add_term("RXN", "K2 * Nx * HOCL")
    msx.add_term("RXNX2", "K2 * Nx * HOCL - K4 * NX2 * HOCL")

    # Add pipe reactions, one per species
    msx.add_reaction("Nx", "pipe", "RATE", "-RXN")
    msx.add_reaction("HOCL", PIPE, RATE, "-RXCL")
    msx.add_reaction("NX2", "p", "r", "RXNX2")

    # Tank reactions actually aren't necessary since there aren't any wall species
    # but it is good form to add them anyway
    msx.add_reaction("Nx", "tank", "rate", "-RXN")
    msx.add_reaction("HOCL", TANK, RATE, "-RXCL")
    msx.add_reaction("NX2", "t", "r", "RXNX2")
    return msx


# ===================== Lead plumbosolvency model
#
def lead_ppm(wn: WaterNetworkModel = None) -> MultispeciesQualityModel:
    r"""A lead plumbosolvency model; please cite [BWMS20]_ if you use this model.

    Parameters
    ----------
    wn : WaterNetworkModel, optional
        the water network to use to hold the new or updated reaction model, by default None

        
    Returns
    -------
    MultispeciesQualityModel
        the new or updated reaction/quality model

        
    Model Description
    -----------------
    This model is described in [BWMS20]_, and represents plumbosolvency of lead in lead pipes
    within a dwelling.

    Bulk species
        .. math::
            PB2 := \mathrm{μg}_\mathrm{(Pb)}~\text{[lead]}

    Coefficients
        .. math::
            M &= 0.117~\mathrm{μg}_{\mathrm{(Pb)}} \, \mathrm{m}^{-2} \, \mathrm{s}^{-1} \\
            E &= 140.0~\mathrm{μg}_{\mathrm{(Pb)}} \, \mathrm{L}^{-1}

    Parameters [1]_
        .. math:: 
            F\langle pipe\rangle = \left\{\begin{matrix}1&\mathrm{if}~pipe~\mathrm{is~lead},\\0&\mathrm{otherwise}\end{matrix}\right.
            
    Pipe reactions [2]_
        .. math::
            \frac{d}{dt}PB2 = F \, Av \, M \frac{\left( E - PB2 \right)}{E}

    Tank reactions
        .. math::
            \frac{d}{dt}PB2 = 0

            
    References
    ----------
    If this model is used, please cite the following paper(s).

    .. [BWMS20]
       J. B. Burkhardt, et al. (2020)
       "Framework for Modeling Lead in Premise Plumbing Systems Using EPANET".
       `Journal of water resources planning and management`.
       **146** (12). https://doi.org/10.1061/(asce)wr.1943-5452.0001304

    Notes
    -----

    .. [1]
       The default value of a parameter is specified by "otherwise" in its mathematical definition. Because
       the values of a parameter are network dependent, the non-global values will need to be added to any
       parameter after the model is added to a network.
    .. [2]
       The hydraulic variable, :math:`Av`, is the surface area per unit volume (area units/L) of the pipe
       where the reaction is taking place. See :numref:`table-msx-hyd-vars` for a list of valid names
       for hydraulic variables that can be used in quality expressions.
    """
    msx = MultispeciesQualityModel()
    msx.name = "lead_ppm"
    msx.title = "Lead Plumbosolvency Model (from Burkhardt et al 2020)"
    msx.desc = "Parameters for EPA HPS Simulator Model"
    msx.references.append(
        """J. B. Burkhardt, et al. (2020) "Framework for Modeling Lead in Premise Plumbing Systems Using EPANET". `Journal of water resources planning and management`. 146(12). https://doi.org/10.1061/(asce)wr.1943-5452.0001304"""
        # dict(
        #     entry_type="article",
        #     key="BWMS20",
        #     fields=dict(
        #         title="Framework for Modeling Lead in Premise Plumbing Systems Using EPANET",
        #         year=2020,
        #         author=[
        #             "Jonathan B. Burkhardt",
        #             "Hyoungmin Woo",
        #             "James Mason",
        #             "Feng Shang",
        #             "Simoni Triantafyllidou",
        #             "Michael R. Schock",
        #             "Darren Lytle",
        #             "Regan Murray",
        #         ],
        #         journaltitle="J Water Resour Plan Manag",
        #         volume=146,
        #         number=12,
        #         date="2020-12-01",
        #         doi="10.1061/(asce)wr.1943-5452.0001304",
        #         eprint=[
        #             "PMID:33627937",
        #             "PMCID:PMC7898126",
        #             "NIHMSID:NIHMS1664627",
        #         ],
        #     ),
        # )
    )
    msx.options = {
        "report": {
            "species": {"PB2": "YES"},
            "species_precision": {"PB2": 5},
            "nodes": "all",
            "links": "all",
        },
        "timestep": 1,
        "area_units": "M2",
        "rate_units": "SEC",
        "rtol": 1e-08,
        "atol": 1e-08,
    }
    PB2 = msx.add_species(name="PB2", species_type=BULK, units="ug", note="dissolved lead (Pb)")
    msx.add_constant("M", 0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-2) * s^(-1)")
    msx.add_constant("E", 140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
    msx.add_parameter("F", global_value=0, note="determines which pipes have reactions")
    PB2.add_reaction("pipes", "RATE", expression="F * Av * M * (E - PB2) / E")
    PB2.add_reaction("tanks", RATE, expression="0")
    return msx


def arsenic_chloramine(wn: WaterNetworkModel = None) -> MultispeciesQualityModel:
    r"""Model monochloramine-arsenite-arsenate adsorption/desorption with fast equilibrium.

    Parameters
    ----------
    wn : WaterNetworkModel, optional
        the water network to use to hold the new or updated reaction model, by default None

    Returns
    -------
    MultispeciesQualityModel
        the new or updated reaction/quality model

    Model Description
    -----------------
    This example models monochloramine oxidation of arsenite/arsenate and wall
    adsorption/desorption, as given in section 3 of the EPANET-MSX user manual.

    The system of equations for the reaction in pipes is given in Eq. (2.4) through (2.7)
    in [SRU23]_.

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

    
    .. list-table:: Coefficients [1]_
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
          - arsenate desporbtion
        * - Smax
          - Const
          - :math:`50.0`
          - :math:`S_{\max}`
          - :math:`\require{upgreek}\upmu\mathrm{g}_{\left(\mathsf{As}^\mathrm{V}\right)}~\mathrm{m}^{-2}`
          - arsenate adsorption limit

    
    .. list-table:: Other terms
        :header-rows: 1
        :widths: 3 3 12 3

        * - Name
          - Symbol
          - Expression
          - Units
        * - Ks
          - :math:`k_s`
          - :math:`{k_1}/{k_2}`
          - :math:`\require{upgreek}\upmu\mathrm{g}^{-1}_{\left(\mathsf{As}^\mathrm{V}\right)}`


    .. list-table:: Pipe reactions [2]_
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

    References
    ----------
    This model is described in the EPANET-MSX user manual [SRU23]_ and was simplified from [GSCL94]_.

    .. [GSCL94]
       B. Gu, J. Schmitt, Z. Chen, L. Liang, and J.F. McCarthy. "Adsorption and desorption of 
       natural organic matter on iron oxide: mechanisms and models". Environ. Sci. Technol., 28:38-46, January 1994.
  
    Notes
    -----

    .. [1]
       The volume unit, :math:`\textrm{L}`, is defined by the network model flow units.
    .. [2]
       The :math:`Av` variable is the surface area per unit volume for the network (by pipe).
       In this model, it has units of :math:`\mathrm{m}^{2} / \mathrm{L}`
    """
    msx = MultispeciesQualityModel()
    msx.title = "Arsenic Oxidation/Adsorption Example"
    msx.add_species(name="AS3", species_type="BULK", units="UG", note="Dissolved arsenite")
    msx.add_species(name="AS5", species_type="BULK", units="UG", note="Dissolved arsenate")
    msx.add_species(name="AStot", species_type="BULK", units="UG", note="Total dissolved arsenic")
    msx.add_species(name="AS5s", species_type="WALL", units="UG", note="Adsorbed arsenate")
    msx.add_species(name="NH2CL", species_type="BULK", units="MG", note="Monochloramine")
    msx.add_constant("Ka", 10.0, units="1 / (MG * HR)", note="Arsenite oxidation rate coefficient")
    msx.add_constant("Kb", 0.1, units="1 / HR", note="Monochloramine decay rate coefficient")
    msx.add_constant("K1", 5.0, units="M^3 / (UG * HR)", note="Arsenate adsorption coefficient")
    msx.add_constant("K2", 1.0, units="1 / HR", note="Arsenate desorption coefficient")
    msx.add_constant("Smax", 50.0, units="UG / M^2", note="Arsenate adsorption limit")
    msx.add_term(name="Ks", expression="K1/K2", note="Equil. adsorption coeff.")
    msx.add_reaction(
        species="AS3", location="pipes", dynamics_type="rate", expression="-Ka*AS3*NH2CL", note="Arsenite oxidation"
    )
    msx.add_reaction(
        "AS5", "pipes", "rate", "Ka*AS3*NH2CL - Av*(K1*(Smax-AS5s)*AS5 - K2*AS5s)", note="Arsenate production less adsorption"
    )
    msx.add_reaction(
        species="NH2CL", location="pipes", dynamics_type="rate", expression="-Kb*NH2CL", note="Monochloramine decay"
    )
    msx.add_reaction("AS5s", "pipe", "equil", "Ks*Smax*AS5/(1+Ks*AS5) - AS5s", note="Arsenate adsorption")
    msx.add_reaction(species="AStot", location="pipes", dynamics_type="formula", expression="AS3 + AS5", note="Total arsenic")
    msx.add_reaction(
        species="AS3", location="tank", dynamics_type="rate", expression="-Ka*AS3*NH2CL", note="Arsenite oxidation"
    )
    msx.add_reaction(
        species="AS5", location="tank", dynamics_type="rate", expression="Ka*AS3*NH2CL", note="Arsenate production"
    )
    msx.add_reaction(
        species="NH2CL", location="tank", dynamics_type="rate", expression="-Kb*NH2CL", note="Monochloramine decay"
    )
    msx.add_reaction(species="AStot", location="tanks", dynamics_type="formula", expression="AS3 + AS5", note="Total arsenic")
    msx.options.area_units = "M2"
    msx.options.rate_units = "HR"
    msx.options.rtol = 0.001
    msx.options.atol = 0.0001
    msx.references.append(cite_msx())
    return msx


def batch_chloramine_decay(wn=None):
    msx = MultispeciesQualityModel()
    msx.title = "Batch chloramine decay example"
    msx.options.area_units = "ft2"
    msx.options.rate_units = "hr"

    msx.add_species("HOCL", "bulk", "mol", note="hypochlorous acid")
    msx.add_species("NH3", "bulk", "mol", note="ammonia")
    msx.add_species("NH2CL", "bulk", "mol", note="monochloramine")
    msx.add_species("NHCL2", "bulk", "mol", note="dichloramine")
    msx.add_species("I", "bulk", "mol", note="unknown intermediate")
    msx.add_species("OCL", "bulk", "mol", note="hypochlorite ion")
    msx.add_species("NH4", "bulk", "mol", note="ammonium ion")
    msx.add_species("ALK", "bulk", "mol", note="total alkalinity")
    msx.add_species("H", "bulk", "mol", note="hydrogen ion")
    msx.add_species("OH", "bulk", "mol", note="hydroxide ion")
    msx.add_species("CO3", "bulk", "mol", note="carbonate ion")
    msx.add_species("HCO3", "bulk", "mol", note="bicarbonate ion")
    msx.add_species("H2CO3", "bulk", "mol", note="dissolved carbon dioxide")
    msx.add_species("chloramine", "bulk", "mmol", note="monochloramine in mmol/L")

    msx.add_parameter("k1", 1.5e10)
    msx.add_parameter("k2", 7.6e-2)
    msx.add_parameter("k3", 1.0e6)
    msx.add_parameter("k4", 2.3e-3)
    msx.add_parameter("k6", 2.2e8)
    msx.add_parameter("k7", 4.0e5)
    msx.add_parameter("k8", 1.0e8)
    msx.add_parameter("k9", 3.0e7)
    msx.add_parameter("k10", 55.0)

    msx.add_term("k5", "(2.5e7*H) + (4.0e4*H2CO3) + (800*HCO3)")
    msx.add_term("a1", "k1 * HOCL * NH3")
    msx.add_term("a2", "k2 * NH2CL")
    msx.add_term("a3", "k3 * HOCL * NH2CL")
    msx.add_term("a4", "k4 * NHCL2")
    msx.add_term("a5", "k5 * NH2CL * NH2CL")
    msx.add_term("a6", "k6 * NHCL2 * NH3 * H")
    msx.add_term("a7", "k7 * NHCL2 * OH")
    msx.add_term("a8", "k8 * I * NHCL2")
    msx.add_term("a9", "k9 * I * NH2CL")
    msx.add_term("a10", "k10 * NH2CL * NHCL2")

    msx.add_reaction("HOCL", PIPE, RATE, "-a1 + a2 - a3 + a4 + a8")
    msx.add_reaction("NH3", PIPE, RATE, "-a1 + a2 + a5 - a6")
    msx.add_reaction("NH2CL", PIPE, RATE, "a1 - a2 - a3 + a4 - a5 + a6 - a9 - a10")
    msx.add_reaction("NHCL2", PIPE, RATE, "a3 - a4 + a5 - a6 - a7 - a8 - a10")
    msx.add_reaction("I", PIPE, RATE, "a7 - a8 - a9")
    msx.add_reaction("H", PIPE, RATE, "0")
    msx.add_reaction("ALK", PIPE, RATE, "0")
    msx.add_reaction("OCL", PIPE, EQUIL, "H * OCL - 3.16E-8 * HOCL")
    msx.add_reaction("NH4", PIPE, EQUIL, "H * NH3 - 5.01e-10 * NH4")
    msx.add_reaction("CO3", PIPE, EQUIL, "H * CO3 - 5.01e-11 * HCO3")
    msx.add_reaction("H2CO3", PIPE, EQUIL, "H * HCO3 - 5.01e-7 * H2CO3")
    msx.add_reaction("HCO3", PIPE, EQUIL, "ALK - HC03 - 2*CO3 - OH + H")
    msx.add_reaction("OH", PIPE, EQUIL, "H * OH - 1.0e-14")
    msx.add_reaction("chloramine", PIPE, FORMULA, "1000 * NH2CL")

    return msx
