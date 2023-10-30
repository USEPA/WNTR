.. raw:: latex

    \clearpage


Errors and debugging
====================

WNTR extends several of the standard python exceptions, :class:`KeyError`, :class:`SyntaxError`,
and :class:`ValueError` with EPANET toolkit specific versions,
:class:`~wntr.epanet.exceptions.ENKeyError`,
:class:`~wntr.epanet.exceptions.ENSyntaxError`,
and :class:`~wntr.epanet.exceptions.ENValueError`,
and a base :class:`~wntr.epanet.exceptions.EpanetException`.
These exceptions are raised when errors occur during INP-file reading/writing, 
when using the EPANET toolkit functions, and when running the 
:class:`~wntr.sim.epanet.EpanetSimulator`.

In addition to the normal information that a similar python exception would provide,
these exceptions return the EPANET error code number and the error description
from the EPANET source code. WNTR also tries to intuit the specific variable,
line number (of an input file), and timestamp to give the user the most information
possible. Tables :numref:`table-epanet-warnings` through :numref:`table-epanet-errors-filesystem`
provide the description of the various warnings and error codes defined in [Ross00]_.


.. _table-epanet-warnings:
.. table:: EPANET warnings

    =========== ==============================================================================================================================================================================  
    *Err No.*   *Description*
    ----------- ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    **1-6**     **Simulation warnings**
    ----------- ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    1           At `{time}`, system hydraulically unbalanced - convergence to a hydraulic solution was not achieved in the allowed number of trials
    2           At `{time}`, system may be hydraulically unstable - hydraulic convergence was only achieved after the status of all links was held fixed
    3           At `{time}`, system disconnected - one or more nodes with positive demands were disconnected for all supply sources
    4           At `{time}`, pumps cannot deliver enough flow or head - one or more pumps were forced to either shut down (due to insufficient head) or operate beyond the maximum rated flow
    5           At `{time}`, valves cannot deliver enough flow - one or more flow control valves could not deliver the required flow even when fully open
    6           At `{time}`, system has negative pressures - negative pressures occurred at one or more junctions with positive demand
    =========== ==============================================================================================================================================================================

.. _table-epanet-errors-runtime:
.. table:: EPANET runtime errors

    =========== =================================================================
    *Err No.*   *Description*
    ----------- -----------------------------------------------------------------
    **101-120** **Runtime and simulation errors**
    ----------- -----------------------------------------------------------------
    101         insufficient memory available
    102         no network data available
    103         hydraulics not initialized
    104         no hydraulics for water quality analysis
    105         water quality not initialized
    106         no results saved to report on
    107         hydraulics supplied from external file
    108         cannot use external file while hydraulics solver is active
    109         cannot change time parameter when solver is active
    110         cannot solve network hydraulic equations
    120         cannot solve water quality transport equations
    =========== =================================================================


.. _table-epanet-errors-network:
.. table:: EPANET network errors

    =========== =================================================================
    *Err No.*   *Description*
    ----------- -----------------------------------------------------------------
    **200-201** **Input file errors (exclusively for input files)**
    ----------- -----------------------------------------------------------------
    200         one or more errors in input file
    201         syntax error
    ----------- -----------------------------------------------------------------
    **202-222** **Input file and toolkit errors**
    ----------- -----------------------------------------------------------------
    202         illegal numeric value
    203         undefined node
    204         undefined link
    205         undefined time pattern
    206         undefined curve
    207         attempt to control a CV/GPV link
    208         illegal PDA pressure limits
    209         illegal node property value
    211         illegal link property value
    212         undefined trace node
    213         invalid option value
    214         too many characters in input line
    215         duplicate ID label
    216         reference to undefined pump
    217         pump has no head curve or power defined
    218         `note: error number 218 is undefined in EPANET 2.2`
    219         illegal valve connection to tank node
    220         illegal valve connection to another valve
    221         misplaced rule clause in rule-based control
    222         link assigned same start and end nodes
    ----------- -----------------------------------------------------------------
    **223-234** **Network consistency errors (INP-file and/or toolkit)**
    ----------- -----------------------------------------------------------------
    223         not enough nodes in network
    224         no tanks or reservoirs in network
    225         invalid lower/upper levels for tank
    226         no head curve or power rating for pump
    227         invalid head curve for pump
    230         nonincreasing x-values for curve
    233         network has unconnected node
    234         network has an unconnected node with ID `id`
    ----------- -----------------------------------------------------------------
    **240-263** **Toolkit-only errors**
    ----------- -----------------------------------------------------------------
    240         nonexistent water quality source
    241         nonexistent control
    250         invalid format (e.g. too long an ID name)
    251         invalid parameter code
    252         invalid ID name
    253         nonexistent demand category
    254         node with no coordinates
    255         invalid link vertex
    257         nonexistent rule
    258         nonexistent rule clause
    259         attempt to delete a node that still has links connected to it
    260         attempt to delete node assigned as a Trace Node
    261         attempt to delete a node or link contained in a control
    262         attempt to modify network structure while a solver is open
    263         node is not a tank
    =========== =================================================================


.. _table-epanet-errors-filesystem:
.. table:: EPANET file/system errors

    =========== =================================================================
    *Err No.*   *Description*
    ----------- -----------------------------------------------------------------
    **301-305** **Filename errors**
    ----------- -----------------------------------------------------------------
    301         identical file names used for different types of files
    302         cannot open input file
    303         cannot open report file
    304         cannot open binary output file
    305         cannot open hydraulics file
    ----------- -----------------------------------------------------------------
    **306-307** **File structure errors**
    ----------- -----------------------------------------------------------------
    306         hydraulics file does not match network data
    307         cannot read hydraulics file
    ----------- -----------------------------------------------------------------
    **308-309** **Filesystem errors**
    ----------- -----------------------------------------------------------------
    308         cannot save results to binary file
    309         cannot save results to report file
    =========== =================================================================


For developers
--------------

The custom exceptions for EPANET that are included in the :class:`wntr.epanet.exceptions`
module subclass both the :class:`~wntr.epanet.exceptions.EpanetException`
and the standard python exception they are named after. This means that when handling
exceptions, a try-catch block that is looking for a :class:`KeyError`, for example,
will still catch an :class:`~wntr.epanet.exceptions.ENKeyError`. The newest versions
of Python, e.g., 3.11, have a new style of multiple inheritence for Exceptions, called
exception groups, but this has not yet been used in WNTR because older versions of
Python are still supported at this time.
