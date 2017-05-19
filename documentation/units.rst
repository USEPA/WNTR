.. raw:: latex

    \clearpage

Units
======================================

All data in WNTR is stored in SI (International System) units:

* Length = :math:`m`
* Diameter = :math:`m`
* Water pressure = :math:`m` (this assumes a fluid density of 1000 :math:`kg/m^3`)
* Elevation = :math:`m`
* Mass = :math:`kg`
* Time = :math:`s`
* Concentration = :math:`kg/m^3`
* Demand = :math:`m^3/s`
* Velocity = :math:`m/s`
* Acceleration = :math:`g` (1 :math:`g` = 9.81 :math:`m/s^2`)
* Energy = :math:`J`
* Power = :math:`W`
* Pressure = :math:`Pa`
* Mass injection = :math:`kg/s`
* Volume = :math:`m^3`

WNTR is compatible with all EPANET unit conventions.  When using an EPANET INP file to 
generate a water network model, WNTR converts model parameters using the units defined in the 
**Units** and **Quality** options of the EPANET INP file.  
These options define the mass and flow units for the model.
Some units also depend on the equation used
for pipe roughness headloss and on the reaction order specified. 
:numref:`table-hydraulic-units`, :numref:`table-quality-units`, and :numref:`table-energy-units` provide 
information on EPANET unit conventions (modified from [Ross00]_).  

.. _table-hydraulic-units:
.. table:: EPANET hydraulic unit conventions.

   +----------------------+-------------------------------------+------------------------------------+
   |   Hydraulic          |   US customary units                |   SI-based units                   |
   |   parameter          |                                     |                                    |
   +======================+=====================================+====================================+
   | Flow                 | *flow* can be defined as:           | *flow* can be defined as:          |
   |                      |                                     |                                    |
   |                      | - CFS: ft :sup:`3` /s               | - LPS: L/s                         |
   |                      | - GPM: gal/min                      | - LPM: L/min                       |
   |                      | - MGD: million gal/day              | - MLD: ML/day                      |
   |                      | - IMGD: million imperial gal/day    | - CMH: m :sup:`3` /hr              |
   |                      | - AFD: acre-feet/day                | - CMD: m :sup:`3` /day             |
   +----------------------+-------------------------------------+------------------------------------+
   | Demand               |   *flow*                            |   *flow*                           |
   +----------------------+-------------------------------------+------------------------------------+
   | Diameter: pipes      |   in                                |   mm                               |
   +----------------------+-------------------------------------+------------------------------------+
   | Diameter: tanks      |   ft                                |   m                                |
   +----------------------+-------------------------------------+------------------------------------+
   | Elevation            |   ft                                |   m                                |
   +----------------------+-------------------------------------+------------------------------------+
   | Hydraulic head       |   ft                                |   m                                |
   +----------------------+-------------------------------------+------------------------------------+
   | Length               |   ft                                |   m                                |
   +----------------------+-------------------------------------+------------------------------------+
   | Emitter coefficient  |   *flow* / sqrt(psi)                |  *flow* / sqrt(m)                  |
   +----------------------+-------------------------------------+------------------------------------+
   | Friction factor      |  unitless                           |  unitless                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Minor loss           |  unitless                           |  unitless                          |
   | coeff.               |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Pressure             |   psi                               |   m   or   kPa                     |
   +----------------------+-------------------------------------+------------------------------------+
   | Roughness coeff:     |   10 :sup:`3` ft                    |   mm                               |
   | D-W                  |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Roughness coeff:     | unitless                            |  unitless                          |
   | H-W, C-M             |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Velocity             |   ft/s                              |   m/s                              |
   +----------------------+-------------------------------------+------------------------------------+
   | Volume               |   ft :sup:`3`                       |   m :sup:`3`                       |
   +----------------------+-------------------------------------+------------------------------------+

.. _table-quality-units:
.. table:: EPANET water quality unit conventions.

   +----------------------+-------------------------------------+------------------------------------+
   | Water quality        | US customary units                  | SI-based units                     |
   | parameter            |                                     |                                    |
   +======================+=====================================+====================================+
   | Concentration        |  *mass* /L where *mass* can be      |  *mass* /L where *mass* can be     |
   |                      |  defined as mg or ug                |  defined as mg or ug               |
   +----------------------+-------------------------------------+------------------------------------+
   | Bulk reaction        |   1/day                             |  1/day                             |
   | coefficient: order-1 |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Wall reaction        |   *mass* /ft :sup:`2` /day          |   *mass* /m :sup:`2` /day          |
   | coefficient: order-0 |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Wall reaction        |   ft/day                            |   m/day                            |
   | coefficient: order-1 |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Reaction rate        |   *mass* /L/day                     | *mass* /L/day                      |
   +----------------------+-------------------------------------+------------------------------------+
   | Source mass          |   *mass* /min                       |   *mass* /min                      |
   | injection rate       |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Water age            |   hours                             | hours                              |
   +----------------------+-------------------------------------+------------------------------------+
   
.. _table-energy-units:
.. table:: EPANET energy unit conventions.

   +----------------------+-------------------------------------+------------------------------------+
   |   Energy parameter   |   US customary units                |   SI-based units                   |
   +======================+=====================================+====================================+
   | Energy               |   kW-hours                          | kW-hours                           |
   +----------------------+-------------------------------------+------------------------------------+
   | Efficiency (pumps)   |   percent                           | percent                            |
   +----------------------+-------------------------------------+------------------------------------+
   | Power                |   hp (horse-power)                  |   kW                               |
   +----------------------+-------------------------------------+------------------------------------+

When running analysis in WNTR, all input values (i.e., time, pressure threshold, node demand) should be specified in SI units. 
All simulation results are also stored in SI units and can be converted to other units if desired.
The SymPy package can be used to convert between units.  The example **converting_units.py**
demonstrates its use.

.. literalinclude:: ../examples/converting_units.py
