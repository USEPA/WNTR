Units
======================================

WNTR is compatible with EPANET formatted water network model input files using the following unit conventions [Ross00]_:

* CFS = cubic feet per second
* GPM = gallons per minute
* MGD = million gallons per day
* IMGD = Imperial mgd
* AFD = acre-feet per day
* LPS = liters per second
* LPM = liters per minute
* MLD = million liters per day
* CMH = cubic meters per hour
* CMD = cubic meters per day

Internally, the water network model is converted to SI (International System) units
(Length = :math:`m`, Mass = :math:`kg`, Time = :math:`s`).
All external data used in the code (i.e., user supplied pressure threshold) should also be in
SI units. Results are stored in SI units and can be converted to other units if desired.

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

The SymPy package can be used to convert between units.  The example **converting_units.py**
demonstrates its use.

.. literalinclude:: ../examples/converting_units.py


EPANET Units
------------

Epanet uses specific internal units depending on the type of Flow Units used.  The following table
provides information on what units EPANET uses. See the ``wntr.epanet.util`` package to learn more
about how to convert units using parameter-based functions.
The mass units are determined by EPANET's `Quality` option, which is actually given in
mass per volume or mass per time. EPANET accepts only the following Quality options:

- mg/L: milligrams per liter (mass unit is `mg`)
- ug/L: micrograms per liter (mass unit is `ug`)
- mg/min: milligrams per minute (mass unit is `mg`)
- ug/min: micrograms per minute (mass unit is `ug`)

The mass units and flow units together determine which units are used for other parameters
within EPANET. Hydraulic parameters do not require knowledge of the mass units, which
are only used in the water quality simulations. Some units also depend on the equation used
for pipe roughness headloss and on the reaction order specified. These are marked in the table
below.

+----------------------+--------------------------------------------------------------------------+
|                      | EPANET flow units ( *flow* ) and mass units ( *mass* )                   |
|                      +-------------------------------------+------------------------------------+
| Parameter            | US Customary (traditional) units    | SI-based (metric) units            |
+======================+=====================================+====================================+
| Flow                 | set *flow* to one of the following: | set *flow* to one of the following:|
|                      |                                     |                                    |
|                      | - CFS ( ft³/s )                     | - LPS ( L/s)                       |
|                      | - GPM ( gal/min )                   | - LPM ( L/min )                    |
|                      | - MGD ( gal/min )                   | - MLD ( ML/day )                   |
|                      | - IMGD ( gal/min )                  | - CMH ( m³/hr )                    |
|                      | - AFD ( acre-feet/day )             | - CMD ( m³/day )                   |
+----------------------+-------------------------------------+------------------------------------+
| Demand               | ( *flow* )                          | ( *flow* )                         |
+----------+-----------+-------------------------------------+------------------------------------+
| Diameter | pipes     | ( in )                              | ( mm )                             |
|          +-----------+-------------------------------------+------------------------------------+
|          | tanks     | ( ft )                              | ( m )                              |
+----------+-----------+-------------------------------------+------------------------------------+
| Elevation            | ( ft )                              | ( m )                              |
+----------------------+-------------------------------------+------------------------------------+
| Hydraulic head       | ( ft )                              | ( m )                              |
+----------------------+-------------------------------------+------------------------------------+
| Length               | ( ft )                              | ( m )                              |
+----------------------+-------------------------------------+------------------------------------+
| Emitter coefficient  | ( *flow* / √psi )                   | ( *flow* / √m )                    |
+----------------------+--------------------------------------------------------------------------+
| Friction factor      | unitless                                                                 |
+----------------------+--------------------------------------------------------------------------+
| Minor loss           | unitless                                                                 |
| coeff.               |                                                                          |
+----------------------+-------------------------------------+------------------------------------+
| Pressure             | ( psi )                             | ( m ) or ( kPa )                   |
+-----------+----------+-------------------------------------+------------------------------------+
| Roughness | D-W      | ( 10⁻³ ft )                         | ( mm )                             |
| coeff.    |          |                                     |                                    |
|           +----------+-------------------------------------+------------------------------------+
|           | H-W, C-M | unitless                                                                 |
+-----------+----------+-------------------------------------+------------------------------------+
| Velocity             | ( ft/s )                            | ( m/s )                            |
+----------------------+-------------------------------------+------------------------------------+
| Volume               | ( ft³ )                             | ( m³ )                             |
+----------------------+-------------------------------------+------------------------------------+
|                                                                                                 |
+----------------------+-------------------------------------+------------------------------------+
| Energy               | ( kW-hours )                                                             |
+----------------------+--------------------------------------------------------------------------+
| Efficiency (pumps)   | ( percent )                                                              |
+----------------------+-------------------------------------+------------------------------------+
| Power                | ( hp )                              | ( kW )                             |
+----------------------+-------------------------------------+------------------------------------+
|                                                                                                 |
+----------------------+-------------------------------------+------------------------------------+
| Concentration        | ( *mass* /L ), where *mass*  is either mg or ug                          |
+----------+-----------+--------------------------------------------------------------------------+
| Bulk     | order-0   | undefined                                                                |
| reaction +-----------+--------------------------------------------------------------------------+
| coeff.   | order-1   | ( 1/day )                                                                |
+----------+-----------+-------------------------------------+------------------------------------+
| Wall     | order-0   | ( *mass* /ft²/day )                 | ( *mass* /m²/day )                 |
| reaction +-----------+-------------------------------------+------------------------------------+
| coeff.   | order-1   | ( ft/day )                          | ( m/day )                          |
+----------+-----------+-------------------------------------+------------------------------------+
| Reaction rate        | ( *mass* /L/day )                                                        |
+----------------------+-------------------------------------+------------------------------------+
| Source mass          | ( *mass* /min )                     | ( *mass* /min )                    |
| injection rate       |                                     |                                    |
+----------------------+-------------------------------------+------------------------------------+
| Water age            | ( hours )                                                                |
+----------------------+--------------------------------------------------------------------------+

