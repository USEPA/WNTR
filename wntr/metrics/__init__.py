"""
The wntr.metrics package contains methods to compute resilience, including
hydraulic, water quality, water security, and economic metrics.  Methods to 
compute topographic metrics are included in the wntr.network.graph module.
"""
from wntr.metrics.hydraulic import expected_demand, average_expected_demand, water_service_availability, todini_index, entropy
from wntr.metrics.water_security import mass_contaminant_consumed, volume_contaminant_consumed, extent_contaminant
from wntr.metrics.economic import annual_network_cost, annual_ghg_emissions, pump_energy
from wntr.metrics.misc import query, population, population_impacted

