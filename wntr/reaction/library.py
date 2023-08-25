# -*- coding: utf-8 -*-
"""
Library of common reactions.

@author: John Burkhart, US EPA ORD
"""

from .model import WaterQualityReactionsModel

nicotine = WaterQualityReactionsModel()
nicotine.options.quality.area_units = 'M2'
nicotine.options.quality.rate_units = 'MIN'
nicotine.options.time.timestep = 1
nicotine.add_bulk_species('Nx', unit='MG', note='Nicotine')
nicotine.add_bulk_species('HOCL', unit='MG', note='Free chlorine')
nicotine.add_constant('kd', value=2.33e-3, unit='min^(-1)', note='decay rate')
nicotine.add_constant('K1', value=5.92e-2, unit='L * min^(-1) * mg^(-1)', note='decay constant for chlorine as function of mass(Nic)')
nicotine.add_constant('K2', value=1.84e-1, unit='L * min^(-1) * mg^(-1)', note='decay constant for nicotine as function of mass(Cl)')
nicotine.add_term('RXCL', expr='kd * HOCL + K1 * Nx * HOCL')
nicotine.add_term('RXN', expr='K2 * Nx * HOCL')
nicotine.add_pipe_reaction('rate', 'Nx', expression='-RXN')
nicotine.add_pipe_reaction('rate', 'HOCL', expression='-RXCL')
nicotine.add_tank_reaction('rate', 'Nx', '0')
nicotine.add_tank_reaction('rate', 'HOCL', '0')

