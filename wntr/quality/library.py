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

"""
import logging

from wntr.utils.citations import Citation
from wntr.quality.multispecies import MultispeciesQualityModel

logger = logging.getLogger(__name__)

# ===================== Nicotine-chlorine model
#
def nicotine() -> MultispeciesQualityModel:
    """A nicotine-chlorine reaction model"""
    msx = MultispeciesQualityModel()
    msx.name = "nicotine"
    msx.title = ("Nicotine - Chlorine reaction",)
    msx.options.area_units = "M2"
    msx.options.rate_units = "MIN"
    msx.options.timestep = 1
    msx.add_bulk_species("Nx", units="MG", note="Nicotine")
    msx.add_bulk_species("HOCL", units="MG", note="Free chlorine")
    msx.add_constant_coeff("kd", global_value=2.33e-3, units="min^(-1)", note="decay rate")
    msx.add_constant_coeff("K1", global_value=5.92e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
    msx.add_constant_coeff("K2", global_value=1.84e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    msx.add_other_term("RXCL", expression="kd * HOCL + K1 * Nx * HOCL")
    msx.add_other_term("RXN", expression="K2 * Nx * HOCL")
    msx.add_pipe_reaction("Nx", "rate", expression="-RXN")
    msx.add_pipe_reaction("HOCL", "rate", expression="-RXCL")
    msx.add_tank_reaction("Nx", "rate", "0")
    msx.add_tank_reaction("HOCL", "rate", "0")
    return msx


# ===================== Nicotine-chlorine reactive intermediate species
#
def nicotine_ri() -> MultispeciesQualityModel:
    """A nicotine-chlorine reaction with a reactive intermediate"""
    msx = MultispeciesQualityModel()
    msx.name = "nicotine_ri"
    msx.title = ("Nicotine - Chlorine reaction with reactive intermediate",)
    # Set the options
    msx.options.area_units = "M2"
    msx.options.rate_units = "MIN"
    msx.options.timestep = 1
    msx.options.atol = 1.0e-10
    msx.options.rtol = 1.0e-10
    # Add species
    msx.add_bulk_species("Nx", units="MG", note="Nicotine")
    msx.add_bulk_species("HOCL", units="MG", note="Free Chlorine")
    msx.add_bulk_species("NX2", units="MG", note="Intermediate Nicotine Reactive")
    # Add coefficients
    msx.add_constant_coeff("kd", 3.0e-5, note="decay rate", units="1/min")
    msx.add_constant_coeff("K1", global_value=9.75e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
    msx.add_constant_coeff("K2", global_value=5.73e-1, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    msx.add_constant_coeff("K3", global_value=1.34e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(N2)")
    msx.add_constant_coeff("K4", global_value=2.19e-2, units="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
    # Add terms (named subexpressions)
    msx.add_other_term("RXCL", expression="kd*HOCL + K1*Nx*HOCL + K3*NX2*HOCL")
    msx.add_other_term("RXN", expression="K2*Nx*HOCL")
    msx.add_other_term("RXNX2", expression="K2*Nx*HOCL - K4*NX2*HOCL")
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
def lead_ppm() -> MultispeciesQualityModel:
    """A lead plumbosolvency model [BWMS20]_.

    .. [BWMS20]
       J. B. Burkhardt, et al. (2020)
       "Framework for Modeling Lead in Premise Plumbing Systems Using EPANET".
       `Journal of water resources planning and management`.
       **146** (12). https://doi.org/10.1061/(asce)wr.1943-5452.0001304

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
    msx.add_constant_coeff("M", global_value=0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-1) * s^(-1)")
    msx.add_constant_coeff("E", global_value=140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
    msx.add_parameterized_coeff("F", global_value=0, note="determines which pipes have reactions")
    msx.add_pipe_reaction("PB2", "RATE", expression="F*Av*M*(E - PB2)/E")
    msx.add_tank_reaction("PB2", "RATE", expression="0")
    return msx
