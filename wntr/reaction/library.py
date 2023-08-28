# -*- coding: utf-8 -*-
"""
Library of common reactions.

@author: John Burkhart, US EPA ORD
"""

from .base import Citation
from .model import WaterQualityReactionsModel

nicotine = WaterQualityReactionsModel(
    title="Nicotine - Chlorine reaction",
    desc="Values in libarary are for test purposes ONLY. These highlight the reaction form/relationship but not necessarily the specific system kinetics. Citations are provided where appropriate for sources of values or models. In most cases updates will be necessary to use for different models -- That is, sources, pipes, nodes are for a given network, and must be updated for different models.",
)
nicotine.options.quality.area_units = "M2"
nicotine.options.quality.rate_units = "MIN"
nicotine.options.time.timestep = 1
nicotine.add_bulk_species("Nx", unit="MG", note="Nicotine")
nicotine.add_bulk_species("HOCL", unit="MG", note="Free chlorine")
nicotine.add_constant_coeff("kd", global_value=2.33e-3, unit="min^(-1)", note="decay rate")
nicotine.add_constant_coeff("K1", global_value=5.92e-2, unit="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
nicotine.add_constant_coeff("K2", global_value=1.84e-1, unit="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
nicotine.add_other_term("RXCL", expression="kd * HOCL + K1 * Nx * HOCL")
nicotine.add_other_term("RXN", expression="K2 * Nx * HOCL")
nicotine.add_pipe_reaction("Nx", "rate", expression="-RXN")
nicotine.add_pipe_reaction("HOCL", "rate", expression="-RXCL")
nicotine.add_tank_reaction("Nx", "rate", "0")
nicotine.add_tank_reaction("HOCL", "rate", "0")


nicotine_ri = WaterQualityReactionsModel(
    title="Nicotine - Chlorine reaction with reactive intermediate",
)
# Set options
nicotine_ri.options.quality.area_units = "M2"
nicotine_ri.options.quality.rate_units = "MIN"
nicotine_ri.options.time.timestep = 1
nicotine_ri.options.quality.atol = 1.0e-10
nicotine_ri.options.quality.rtol = 1.0e-10

# Add species
nicotine_ri.add_bulk_species("Nx", unit="MG", note="Nicotine")
nicotine_ri.add_bulk_species("HOCL", unit="MG", note="Free Chlorine")
nicotine_ri.add_bulk_species("NX2", unit="MG", note="Intermediate Nicotine Reactive")

# Add coefficients
nicotine_ri.add_constant_coeff("kd", 3.0e-5, note="decay rate", unit="1/min")
nicotine_ri.add_constant_coeff("K1", global_value=9.75e-2, unit="L * min^(-1) * mg^(-1)", note="decay constant for chlorine as function of mass(Nic)")
nicotine_ri.add_constant_coeff("K2", global_value=5.73e-1, unit="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")
nicotine_ri.add_constant_coeff("K3", global_value=1.34e-2, unit="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(N2)")
nicotine_ri.add_constant_coeff("K4", global_value=2.19e-2, unit="L * min^(-1) * mg^(-1)", note="decay constant for nicotine as function of mass(Cl)")

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


lead_ppm = WaterQualityReactionsModel(
    title="Lead Plumbosolvency Model (from Burkhardt et al 2020)",
    desc="Parameters for EPA HPS Simulator Model",
    citations=Citation(
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
        citationtype="article",
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
    ),
    allow_sympy_reserved_names=True,
    options={
        "time": {"timestep": 1},
        "report": {
            "species": {"PB2": "YES"},
            "species_precision": {"PB2": 5},
            "nodes": "all",
            "links": "all",
        },
        "quality": {
            "area_units": "M2",
            "rate_units": "SEC",
            "rtol": 1e-08,
            "atol": 1e-08,
        },
    },
)
lead_ppm.options.quality.area_units = "M2"
lead_ppm.options.quality.rate_units = "SEC"
lead_ppm.options.quality.rtol = 1.0e-8
lead_ppm.options.quality.atol = 1.0e-8
lead_ppm.options.time.timestep = 1

lead_ppm.add_bulk_species("PB2", "ug", note="dissolved lead (Pb)")
lead_ppm.add_constant_coeff("M", global_value=0.117, note="Desorption rate (ug/m^2/s)", unit="ug * m^(-1) * s^(-1)")
lead_ppm.add_constant_coeff("E", global_value=140.0, note="saturation/plumbosolvency level (ug/L)", unit="ug/L")
lead_ppm.add_parameterized_coeff("F", global_value=0, note="determines which pipes have reactions")
lead_ppm.add_pipe_reaction("PB2", "RATE", expression="F*Av*M*(E - PB2)/E")
lead_ppm.add_tank_reaction("PB2", "RATE", expression="0")
