Units
======================================

All data in WNTR is stored in SI (International System) units:

* Length = :math:`m`
* Diameter = :math:`m`
* Water pressure = :math:`m`
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
generate a water network model, WNTR uses the specific internal units defined by the 
**Units** and **Quality** options in the EPANET INP file.  
Together, these define the mass and flow units for the model.
Some units also depend on the equation used
for pipe roughness headloss and on the reaction order specified. 
:numref:`table-units` provides information on EPANET unit conventions (modified from [Ross00]_).  

.. _table-units:
.. table:: EPANET unit conventions.

   +----------------------+-------------------------------------+------------------------------------+
   | **Hydraulic**        | **US Customary units**              | **SI-based units**                 |
   | **Parameter**        |                                     |                                    |
   +======================+=====================================+====================================+
   | Flow                 | *flow* can be defined as:           | *flow* can be defined as:          |
   |                      |                                     |                                    |
   |                      | - CFS: ft³/s                        | - LPS: L/s                         |
   |                      | - GPM: gal/min                      | - LPM: L/min                       |
   |                      | - MGD: million gal/day              | - MLD: ML/day                      |
   |                      | - IMGD: million imperial gal/day    | - CMH: m³/hr                       |
   |                      | - AFD: acre-feet/day                | - CMD: m³/day                      |
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
   | Emitter coefficient  |   *flow* / vpsi                     |  *flow* / vm                       |
   +----------------------+-------------------------------------+------------------------------------+
   | Friction factor      | unitless                                                                 |
   +----------------------+--------------------------------------------------------------------------+
   | Minor loss           | unitless                                                                 |
   | coeff.               |                                                                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Pressure             |   psi                               |   m   or   kPa                     |
   +----------------------+-------------------------------------+------------------------------------+
   | Roughness coeff:     |   10?³ ft                           |   mm                               |
   | D-W                  |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Roughness coeff:     | unitless                                                                 |
   | H-W, C-M             |                                                                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Velocity             |   ft/s                              |   m/s                              |
   +----------------------+-------------------------------------+------------------------------------+
   | Volume               |   ft³                               |   m³                               |
   +----------------------+-------------------------------------+------------------------------------+
   | **Energy Parameter** | **US Customary units**              | **SI-based units**                 |
   +----------------------+-------------------------------------+------------------------------------+
   | Energy               |   kW-hours                                                               |
   +----------------------+--------------------------------------------------------------------------+
   | Efficiency (pumps)   |   percent                                                                |
   +----------------------+-------------------------------------+------------------------------------+
   | Power                |   hp (horse-power)                  |   kW                               |
   +----------------------+-------------------------------------+------------------------------------+
   | **Water Quality**    | **US Customary units**              | **SI-based units**                 |
   | **Parameter**        |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Concentration        |   *mass* /L ,  where *mass*  can be defined as mg or ug                  |
   +----------------------+--------------------------------------------------------------------------+
   | Bulk reaction        |   1/day                                                                  |
   | coefficient: order-1 |                                                                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Wall reaction        |   *mass* /ft²/day                   |   *mass* /m²/day                   |
   | coefficient: order-0 |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Wall reaction        |   ft/day                            |   m/day                            |
   | coefficient: order-1 |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Reaction rate        |   *mass* /L/day                                                          |
   +----------------------+-------------------------------------+------------------------------------+
   | Source mass          |   *mass* /min                       |   *mass* /min                      |
   | injection rate       |                                     |                                    |
   +----------------------+-------------------------------------+------------------------------------+
   | Water age            |   hours                                                                  |
   +----------------------+--------------------------------------------------------------------------+

When running analysis in WNTR, all input values (i.e., time, pressure threshold, node demand) should be specified in SI units. 
All simulation results are also stored in SI units and can be converted to other units if desired.
The SymPy package can be used to convert between units.  The example **converting_units.py**
demonstrates its use.

.. literalinclude:: ../examples/converting_units.py
