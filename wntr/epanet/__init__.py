u"""Provide EPANET2 compatibility functions for WNTR.


Units
=====
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


======================  ====================================  =====================================
Parameter               US Customary (traditional)            SI-based (metric)
======================  ====================================  =====================================
.                       **Hydraulics/Energy**

Flow                    - CFS ( ft\u00B3 / s )                     - LPS ( L / s )
                        - GPM ( gal / min )                   - LPM ( L / min )
                        - MGD ( million gal / day )           - MLD ( ML / day )
                        - IMGD ( Imperial MGD )               - CMH ( m\u00B3 / hr )
                        - AFD ( acre-feet / day )             - CMD ( m\u00B3 / day )
Demand                  ( *flow units* )                      ( *flow units* )
Diameter (Pipes)        ( in )                                ( mm )
Diameter (Tanks)        ( ft )                                ( m )
Efficiency              ( \% )                                ( \% )
Elevation               ( ft )                                ( m )
Emitter Coefficient     ( *flow units* / (\u221Apsi) )             ( *flow units* / (\u221Am) )
Energy                  (kW hrs)                              (kW hrs)
Friction Factor         unitless                              unitless
Hydraulic Head          (ft)                                  ( m )
Length                  (ft)                                  ( m )
Minor Loss Coeff.       unitless                              unitless
Power                   (HP)                                  (kW)
Pressure                (psi)                                 ( m )
Roughness Coefficient   - (10\u207B\u00B3 ft) [Darcy-Weisbach eqn.]     - ( mm ) [Darcy-Weisbach eqn.]
                        - unitless [otherwise]                - unitless [otherwise]
Velocity                (ft / s)                              (m / s)
Volume                  (ft\u00B3)                                 (m\u00B3)

.                       **Water Quality**

Concentration           ( *mass units* / L)                   ( *mass units* / L)
Bulk Reaction Coeff.    - undefined [0-order]                 - undefined [0-order]
                        - ( 1 / day ) [1st-order]             - ( 1 / day ) [1st-order]
Wall Reaction Coeff.    - (MASS / ft\u00B2 / day) [0-order]        - (MASS / m\u00B2 / day) [0-order]
                        - ( ft / day ) [1st-order]            - ( m / day ) [1st-order]
Source Mass Inj. Rate   ( *mass units* / min )                ( *mass units* / min )
Water Age               ( hrs )                               ( hrs )
======================  ====================================  =====================================




The following classes and functions are automatically imported

.. rubric:: Classes

.. autosummary::

    InpFile
    RptFile
    BinFile
    HydFile
    EpanetSimulator


.. rubric:: Parameter Units Conversion (Enum) Classes

.. autosummary::

    FlowUnits
    MassUnits
    HydParam
    QualParam


"""

from .io import InpFile, BinFile, HydFile, RptFile
from .util import FlowUnits, MassUnits, HydParam, QualParam
from .sim import EpanetSimulator
from . import pyepanet
