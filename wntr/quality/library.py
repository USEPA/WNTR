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

    Make sure to provide all appropriate citations to the model in your creation 
    function.
"""

import logging

from wntr.utils.citations import Citation
from wntr.quality.multispecies import MultispeciesQualityModel
from wntr.network.model import WaterNetworkModel

logger = logging.getLogger(__name__)


##########################################
##
##  IMPORTANT NOTE FOR CONTRIBUTORS
##
## The docstrings you write will likely use mathematics, as with the models already provided.
## you will need to make them "raw" strings -- i.e.,   r"""adocstring"""
## This is because most latex/mathjax formats use \ characters, which mess up docscrape
## unless you mark the string as raw, not interpreted, text.
##

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
            K_1 &= 5.92 \times 10^{-2}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Nic)}}^{-1} \\
            K_2 &= 1.83 \times 10^{-1}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Cl)}}^{-1}

    Other terms
        .. math::

            RxCl &= k_d \cdot HOCL + K_1 \cdot Nx \cdot HOCL \\
            RxN &= K_2 \cdot Nx \cdot HOCL

    Pipe reactions
        .. math::

            \frac{d}{dt}Nx &= -RxN \\
            \frac{d}{dt}HOCL &= -RxCl

    The tank reactions are not explicitly defined in this model.


    Notes
    -----
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
    msx = MultispeciesQualityModel()
    msx.name = "nicotine"
    msx.title = ("Nicotine - Chlorine reaction",)
    msx.options.area_units = "m2"
    msx.options.rate_units = "min"
    msx.options.timestep = 1
    msx.add_bulk_species("Nx", units="mg", note="Nicotine")
    msx.add_bulk_species("HOCL", units="mg", note="Free chlorine")
    msx.add_constant_coeff("kd", global_value=2.33e-3, units="min^(-1)", note="decay rate")
    msx.add_constant_coeff("K1", global_value=5.92e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
    msx.add_constant_coeff("K2", global_value=1.84e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    msx.add_other_term("RxCl", expression="kd * HOCL + K1 * Nx * HOCL")
    msx.add_other_term("RxN", expression="K2 * Nx * HOCL")
    msx.add_pipe_reaction("Nx", "rate", expression="-RxN")
    msx.add_pipe_reaction("HOCL", "rate", expression="-RxCl")
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
            K_1 &= 9.75 \times 10^{-2}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Nic)}}^{-1}\\
            K_2 &= 5.73 \times 10^{-1}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Cl)}}^{-1}\\
            K_3 &= 1.34 \times 10^{-2}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Nic_2)}}^{-1}\\
            K_4 &= 2.19 \times 10^{-2}~\mathrm{L}\cdot\mathrm{min}^{-1}\cdot\mathrm{mg}_{\mathrm{(Cl)}}^{-1}

    Other terms
        .. math:: 
            RXCL &= k_d \cdot HOCL + K_1 \cdot Nx \cdot HOCL + K_3 \cdot NX2 \cdot HOCL\\
            RXN &= K_2 \cdot Nx \cdot HOCL\\
            RXNX2 &= K_2 \cdot Nx \cdot HOCL - K_4 \cdot NX2 \cdot HOCL

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
    msx.add_bulk_species("Nx", units="mg", note="Nicotine")
    msx.add_bulk_species("HOCL", units="mg", note="Free Chlorine")
    msx.add_bulk_species("NX2", units="mg", note="Intermediate Nicotine Reactive")
    # Add coefficients
    msx.add_constant_coeff("kd", 3.0e-5, note="decay rate", units="1/min")
    msx.add_constant_coeff("K1", global_value=9.75e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
    msx.add_constant_coeff("K2", global_value=5.73e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    msx.add_constant_coeff("K3", global_value=1.34e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Nic2)")
    msx.add_constant_coeff("K4", global_value=2.19e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    # Add terms (named subexpressions)
    msx.add_other_term("RXCL", expression="kd * HOCL + K1 * Nx * HOCL + K3 * NX2 * HOCL")
    msx.add_other_term("RXN", expression="K2 * Nx * HOCL")
    msx.add_other_term("RXNX2", expression="K2 * Nx * HOCL - K4 * NX2 * HOCL")
    # Add pipe reactions, one per species
    msx.add_pipe_reaction("Nx", "RATE", expression="-RXN")
    msx.add_pipe_reaction("HOCL", "RATE", expression="-RXCL")
    msx.add_pipe_reaction("NX2", "RATE", expression="RXNX2")
    # Tank reactions actually aren't necessary since there aren't any wall species
    msx.add_tank_reaction("Nx", "RATE", expression="-RXN")
    msx.add_tank_reaction("HOCL", "RATE", expression="-RXCL")
    msx.add_tank_reaction("NX2", "RATE", expression="RXNX2")
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
            M &= 0.117~\mathrm{μg}_{\mathrm{(Pb)}} \cdot \mathrm{m}^{-2} \cdot \mathrm{s}^{-1} \\
            E &= 140.0~\mathrm{μg}_{\mathrm{(Pb)}} \cdot \mathrm{L}^{-1}

    Parameters [1]_
        .. math:: 
            F\langle pipe\rangle = \left\{\begin{matrix}1&\mathrm{if}~pipe~\mathrm{is~lead},\\0&\mathrm{otherwise}\end{matrix}\right.
            
    Pipe reactions [2]_
        .. math::
            \frac{d}{dt}PB2 = F \cdot Av \cdot M \frac{\left( E - PB2 \right)}{E}

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
    If a water network is provided that does not have an ``msx`` attribute, then a new model will be
    created and added to the network. The new model will also be returned as an object.
    
    If a water network is provided that already has an ``msx`` attribute, then this function will:
    first check to see if there are variables that are in conflict with the existing reaction
    model. If there are conflicts, an exception will be raised. The :attr:`~MultispeciesOptions.area_units`
    and :attr:`~MultispeciesOptions.rate_units` will also be checked for conflicts, and an exception raised
    if they differ.
    If there are no conflicts, then the variables and reactions for this model will be added to the
    existing model. If there are conflicts, then the user must resolve them and try again.

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
    msx.citations.append(
        Citation(
            "article",
            "BWMS20",
            fields=dict(
                title="Framework for Modeling Lead in Premise Plumbing Systems Using EPANET",
                year=2020,
                author=[
                    "Jonathan B. Burkhardt",
                    "Hyoungmin Woo",
                    "James Mason",
                    "Feng Shang",
                    "Simoni Triantafyllidou",
                    "Michael R. Schock",
                    "Darren Lytle",
                    "Regan Murray",
                ],
                journaltitle="J Water Resour Plan Manag",
                volume=146,
                number=12,
                date="2020-12-01",
                doi="10.1061/(asce)wr.1943-5452.0001304",
                eprint=[
                    "PMID:33627937",
                    "PMCID:PMC7898126",
                    "NIHMSID:NIHMS1664627",
                ],
            ),
        )
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
    msx.add_bulk_species("PB2", "ug", note="dissolved lead (Pb)")
    msx.add_constant_coeff("M", global_value=0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-2) * s^(-1)")
    msx.add_constant_coeff("E", global_value=140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
    msx.add_parameterized_coeff("F", global_value=0, note="determines which pipes have reactions")
    msx.add_pipe_reaction("PB2", "RATE", expression="F * Av * M * (E - PB2) / E")
    msx.add_tank_reaction("PB2", "RATE", expression="0")
    return msx
