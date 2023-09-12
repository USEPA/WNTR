# -*- coding: utf-8 -*-
# @Contributors:
#   Jonathan Burkhardt, U.S. Environmental Protection Agency, Office of Research and Development

"""
A library of common reactions.
Values in libarary are for test purposes ONLY. These highlight the reaction form/relationship 
but not necessarily the specific system kinetics. Citations are provided where appropriate for 
sources of values or models. In most cases updates will be necessary to use for different 
models - that is, sources, pipes, nodes are for a given network, and must be updated for different 
models.

.. autosummary::

    nicotine
    nicotine_ri
    lead_ppm

"""
import logging

from ..utils.citations import Citation
from .model import WaterQualityReactionsModel

logger = logging.getLogger(__name__)

# ===================== Nicotine-chlorine model
#
nicotine = WaterQualityReactionsModel(
    title="Nicotine - Chlorine reaction",
    desc="Values in libarary are for test purposes ONLY.",
)
"""A nicotine-chlorine reaction model"""

nicotine.options.quality.area_units = "M2"
nicotine.options.quality.rate_units = "MIN"
nicotine.options.quality.timestep = 1
nicotine.add_bulk_species("Nx", units="MG", note="Nicotine")
nicotine.add_bulk_species("HOCL", units="MG", note="Free chlorine")
nicotine.add_constant_coeff("kd", global_value=2.33e-3, units="min^(-1)", note="decay rate")
nicotine.add_constant_coeff("K1", global_value=5.92e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
nicotine.add_constant_coeff("K2", global_value=1.84e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
nicotine.add_other_term("RXCL", expression="kd * HOCL + K1 * Nx * HOCL")
nicotine.add_other_term("RXN", expression="K2 * Nx * HOCL")
nicotine.add_pipe_reaction("Nx", "rate", expression="-RXN")
nicotine.add_pipe_reaction("HOCL", "rate", expression="-RXCL")
nicotine.add_tank_reaction("Nx", "rate", "0")
nicotine.add_tank_reaction("HOCL", "rate", "0")

# ===================== Nicotine-chlorine reactive intermediate species
#
nicotine_ri = WaterQualityReactionsModel(
    title="Nicotine - Chlorine reaction with reactive intermediate",
    desc="Values in libarary are for test purposes ONLY.",
)
"""A nicotine-chlorine reaction with a reactive intermediate"""
# Set the options
nicotine_ri.options.quality.area_units = "M2"
nicotine_ri.options.quality.rate_units = "MIN"
nicotine_ri.options.quality.timestep = 1
nicotine_ri.options.quality.atol = 1.0e-10
nicotine_ri.options.quality.rtol = 1.0e-10
# Add species
nicotine_ri.add_bulk_species("Nx", units="MG", note="Nicotine")
nicotine_ri.add_bulk_species("HOCL", units="MG", note="Free Chlorine")
nicotine_ri.add_bulk_species("NX2", units="MG", note="Intermediate Nicotine Reactive")
# Add coefficients
nicotine_ri.add_constant_coeff("kd", 3.0e-5, note="decay rate", units="1/min")
nicotine_ri.add_constant_coeff("K1", global_value=9.75e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
nicotine_ri.add_constant_coeff("K2", global_value=5.73e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
nicotine_ri.add_constant_coeff("K3", global_value=1.34e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(N2)")
nicotine_ri.add_constant_coeff("K4", global_value=2.19e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
# Add terms (named subexpressions)
nicotine_ri.add_other_term("RXCL", expression="kd*HOCL + K1*Nx*HOCL + K3*NX2*HOCL")
nicotine_ri.add_other_term("RXN", expression="K2*Nx*HOCL")
nicotine_ri.add_other_term("RXNX2", expression="K2*Nx*HOCL - K4*NX2*HOCL")
# Add pipe reactions, one per species
nicotine_ri.add_pipe_reaction("Nx", "RATE", expression="-RXN")
nicotine_ri.add_pipe_reaction("HOCL", "RATE", expression="-RXCL")
nicotine_ri.add_pipe_reaction("NX2", "RATE", expression="RXNX2")
# Tank reactions actually aren't necessary since there aren't any wall species
nicotine_ri.add_tank_reaction("Nx", "RATE", expression="-RXN")
nicotine_ri.add_tank_reaction("HOCL", "RATE", expression="-RXCL")
nicotine_ri.add_tank_reaction("NX2", "RATE", expression="RXNX2")

# ===================== Lead plumbosolvency model
#
lead_ppm = WaterQualityReactionsModel(
    title="Lead Plumbosolvency Model (from Burkhardt et al 2020)",
    desc="Parameters for EPA HPS Simulator Model",
    citations=[Citation( 
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
        citation_class="article",
        journaltitle="J Water Resour Plan Manag",
        volume=146,
        number=12,
        fulldate="2020-12-01",
        doi="10.1061/(asce)wr.1943-5452.0001304",
        eprint=[
            "PMID:33627937",
            "PMCID:PMC7898126",
            "NIHMSID:NIHMS1664627",
        ],
    )],
    allow_sympy_reserved_names=True,
    options={
        "report": {
            "species": {"PB2": "YES"},
            "species_precision": {"PB2": 5},
            "nodes": "all",
            "links": "all",
        },
        "quality": {
            "timestep": 1,
            "area_units": "M2",
            "rate_units": "SEC",
            "rtol": 1e-08,
            "atol": 1e-08,
        },
    },
)
"""A lead plumbosolvency model [BEMS20]_.

.. [BEMS20]
   J. B. Burkhardt, et al. (2020) 
   "Framework for Modeling Lead in Premise Plumbing Systems Using EPANET". 
   `Journal of water resources planning and management`. 
   **146** (12). 
   https://doi.org/10.1061/(asce)wr.1943-5452.0001304

"""
# add the species, coefficients and reactions
lead_ppm.add_bulk_species("PB2", "ug", note="dissolved lead (Pb)")
lead_ppm.add_constant_coeff("M", global_value=0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-1) * s^(-1)")
lead_ppm.add_constant_coeff("E", global_value=140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
lead_ppm.add_parameterized_coeff("F", global_value=0, note="determines which pipes have reactions")
lead_ppm.add_pipe_reaction("PB2", "RATE", expression="F*Av*M*(E - PB2)/E")
lead_ppm.add_tank_reaction("PB2", "RATE", expression="0")
