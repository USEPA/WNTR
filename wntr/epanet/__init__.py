u"""Provide EPANET2 compatibility functions for WNTR.

EPANET Units
------------

The EPANET units and conversions are described here for easy reference. The units
used by EPANET depend on the `Flow Units` and the `Mass Units` specified in the input
file. The list below show the various units accepted by EPANET; WNTR converts to and uses
SI units (cubic meters per second) internally.

- CFS: cubic feet per second
- GPM: gallons per minute
- MGD: million gallons per day
- IMGD: million imperial gallons per day
- AFD: acre-feet per day
- LPS: liters per second
- LPM: liters per minute
- MLD: megaliters per day
- CMH: cubic meters per hour
- CMD: cubic meters per day

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
|                      | - CFS ( ft\u00B3/s )                     | - LPS ( L/s)                       |
|                      | - GPM ( gal/min )                   | - LPM ( L/min )                    |
|                      | - MGD ( gal/min )                   | - MLD ( ML/day )                   |
|                      | - IMGD ( gal/min )                  | - CMH ( m\u00B3/hr )                    |
|                      | - AFD ( acre-feet/day )             | - CMD ( m\u00B3/day )                   |
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
| Emitter coefficient  | ( *flow* / \u221Apsi )                   | ( *flow* / \u221Am )                    |
+----------------------+--------------------------------------------------------------------------+
| Friction factor      | unitless                                                                 |
+----------------------+--------------------------------------------------------------------------+
| Minor loss           | unitless                                                                 |
| coeff.               |                                                                          |
+----------------------+-------------------------------------+------------------------------------+
| Pressure             | ( psi )                             | ( m ) or ( kPa )                   |
+-----------+----------+-------------------------------------+------------------------------------+
| Roughness | D-W      | ( 10\u207B\u00B3 ft )                         | ( mm )                             |
| coeff.    |          |                                     |                                    |
|           +----------+-------------------------------------+------------------------------------+
|           | H-W, C-M | unitless                                                                 |
+-----------+----------+-------------------------------------+------------------------------------+
| Velocity             | ( ft/s )                            | ( m/s )                            |
+----------------------+-------------------------------------+------------------------------------+
| Volume               | ( ft\u00B3 )                             | ( m\u00B3 )                             |
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
| Wall     | order-0   | ( *mass* /ft\u00B2/day )                 | ( *mass* /m\u00B2/day )                 |
| reaction +-----------+-------------------------------------+------------------------------------+
| coeff.   | order-1   | ( ft/day )                          | ( m/day )                          |
+----------+-----------+-------------------------------------+------------------------------------+
| Source mass          | ( *mass* /min )                     | ( *mass* /min )                    |
| injection rate       |                                     |                                    |
+----------------------+-------------------------------------+------------------------------------+
| Water age            | ( hours )                                                                |
+----------------------+--------------------------------------------------------------------------+


"""


from .io import InpFile, BinFile, HydFile, RptFile
from .util import FlowUnits, MassUnits, HydParam, QualParam
from .sim import EpanetSimulator
import pyepanet

