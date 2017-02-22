"""
The wntr.metrics package contains methods to compute resilience, including
hydraulic, water quality, water security, and economic metrics.  Methods to 
compute topographic metrics are included in the wntr.network.graph module.
"""
from wntr.metrics.todini import todini
from wntr.metrics.entropy import entropy
from wntr.metrics.cost import cost
from wntr.metrics.ghg_emissions import ghg_emissions
from wntr.metrics.health_impacts import average_water_consumed, population, population_impacted
from wntr.metrics.health_impacts import mass_contaminant_consumed, volume_contaminant_consumed, extent_contaminant
from wntr.metrics.fraction_delivered import fdv, fdd, fdq
from wntr.metrics.query import query

