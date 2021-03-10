.. raw:: latex

    \clearpage

.. _options:

Options
================================

Water network options are stored in an :class:`~wntr.network.options.Options` 
class which divides options into the following sections:

* :class:`~wntr.network.options.TimeOptions`: Options related to simulation and model timing
* :class:`~wntr.network.options.HydraulicOptions`: Options related to hydraulic modeling
* :class:`~wntr.network.options.QualityOptions`: Options related to water quality modeling
* :class:`~wntr.network.options.ReactionOptions`: Options related to water quality reactions
* :class:`~wntr.network.options.EnergyOptions`: Options related to energy calculations
* :class:`~wntr.network.options.ReportOptions`: Options related to reporting
* :class:`~wntr.network.options.GraphicsOptions`: Options related to graphics
* :class:`~wntr.network.options.UserOptions`: Options defined by the user

All of these options can be modified in WNTR and then written to an EPANET INP file.

The options are appended to the WaterNetworkModel. 
In the example below, an empty WaterNetworkModel is created and the options 
are set to default values.  If the WaterNetworkModel is created using an EPANET INP file,
then the options are defined using values from that file. 

.. doctest::
    :hide:

    >>> import wntr

.. doctest::

    >>> wn = wntr.network.model.WaterNetworkModel()
    >>> wn.options  # doctest: +SKIP

Individual sections are selected as follows.

.. doctest::

    >>> wn.options.time  # doctest: +SKIP
    >>> wn.options.hydraulic  # doctest: +SKIP
    >>> wn.options.quality  # doctest: +SKIP
    >>> wn.options.reaction  # doctest: +SKIP
    >>> wn.options.energy  # doctest: +SKIP
    >>> wn.options.report  # doctest: +SKIP
    >>> wn.options.graphics  # doctest: +SKIP
    >>> wn.options.user  # doctest: +SKIP

Options can be modified, as shown in the example below.

.. doctest::
    
    >>> wn.options.time.duration = 86400
    >>> wn.options.hydraulic.demand_model = 'PDD'
    >>> wn.options.hydraulic.required_pressure = 21.097 # 30 psi = 21.097 m
	
Note that EPANET 2.0.12 does not use the demand model, minimum pressure, 
required pressure, or pressure exponent from the hydraulic section.
Options that directly apply to hydraulic simulation that are not used in the
WNTRSimulator are described in :ref:`limitations`.  

The easiest way to view options is to print the options as a dictionary. 
For example, hydraulic options are shown below.

.. doctest::

	>>> print(dict(wn.options.hydraulic)) # doctest: +SKIP
	{'accuracy': 0.001,
	 'checkfreq': 2,
	 'damplimit': 0.0,
	 'demand_model': None,
	 'demand_multiplier': 1.0,
	 ...
