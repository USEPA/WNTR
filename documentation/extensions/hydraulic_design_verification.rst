**Summary:** The ``design_verification`` extension applies proposed pipe
diameter changes and WNTR time and hydraulic simulation options to
independent copies of a WNTR water-distribution network model. It runs
hydraulic simulations and checks whether pressure, velocity and pump
operating requirements are satisfied. The verification scope is limited
to pipe diameters and the WNTR time and hydraulic option groups.
Additional pipe parameters and operating conditions, including controls,
are not included in the verification.

**Point of contact:** Rheal Thomas,
https://github.com/thom1505

Overview
--------

The extension provides a repeatable hydraulic-verification layer for
design, rehabilitation, optimisation and scenario-analysis workflows.

It can:

* apply proposed pipe diameters without modifying the original network;
* apply WNTR time and hydraulic simulation options;
* run simulations using ``WNTRSimulator`` or ``EpanetSimulator``;
* assess minimum junction pressure;
* assess maximum absolute pipe velocity;
* audit head-pump flows against the maximum flow represented by their
  pump curves;
* identify critical components and simulation times;
* calculate compliance percentages;
* return an overall hydraulic-feasibility result; and
* produce an audit record describing the verification run.

Overall feasibility
-------------------

A verification is feasible only when:

* the required pressure compliance is achieved;
* the required velocity compliance is achieved; and
* all head pumps pass the pump-curve audit.

A network containing no head pumps does not fail solely because the
pump audit is not applicable.

Basic use
---------

A hydraulic scenario uses WNTR's native simulation options:

.. doctest::

   >>> from wntr.network import Options
   >>> from wntr.extensions.design_verification import HydraulicScenario
   >>> options = Options()
   >>> options.hydraulic.demand_model = "DD"
   >>> options.time.duration = 0
   >>> options.time.hydraulic_timestep = 3600
   >>> options.time.report_timestep = 3600
   >>> scenario = HydraulicScenario(
   ...     name="Baseline DD",
   ...     options=options,
   ... )
   >>> scenario.name
   'Baseline DD'
   >>> isinstance(scenario.options, Options)
   True

The following doctest builds a small water network, applies a candidate
pipe-diameter design and hydraulic simulation options, and verifies the
result against pressure and velocity constraints.

.. doctest::

   >>> import wntr
   >>> from wntr.extensions.design_verification import (
   ...     HydraulicScenario,
   ...     PipeDesign,
   ...     run_design_verification,
   ... )
   >>> wn = wntr.network.WaterNetworkModel()
   >>> wn.add_reservoir(
   ...     "R1",
   ...     base_head=50.0,
   ...     coordinates=(0.0, 0.0),
   ... )
   >>> wn.add_junction(
   ...     "J1",
   ...     base_demand=0.01,
   ...     demand_pattern=None,
   ...     elevation=10.0,
   ...     coordinates=(100.0, 0.0),
   ... )
   >>> wn.add_pipe(
   ...     "P1",
   ...     start_node_name="R1",
   ...     end_node_name="J1",
   ...     length=100.0,
   ...     diameter=0.150,
   ...     roughness=100.0,
   ...     minor_loss=0.0,
   ... )
   >>> options = wntr.network.Options()
   >>> options.time.duration = 0
   >>> options.time.hydraulic_timestep = 3600
   >>> options.time.report_timestep = 3600
   >>> options.hydraulic.demand_model = "DD"
   >>> options.hydraulic.demand_multiplier = 1.0
   >>> scenario = HydraulicScenario(
   ...     name="Baseline",
   ...     options=options,
   ... )
   >>> design = PipeDesign(
   ...     name="Candidate pipe design",
   ...     diameters_m={"P1": 0.200},
   ... )
   >>> verification, hydraulic_results, audit = run_design_verification(
   ...     wn=wn,
   ...     scenario=scenario,
   ...     design=design,
   ...     simulator="WNTRSimulator",
   ...     minimum_pressure_m=15.0,
   ...     maximum_velocity_mps=2.5,
   ... )
   >>> print(f"Overall verification feasible: {verification.feasible}")
   Overall verification feasible: True
   >>> print(
   ...     "Minimum-pressure constraint satisfied: "
   ...     f"{verification.pressure_result.feasible}"
   ... )
   Minimum-pressure constraint satisfied: True
   >>> print(
   ...     "Maximum-velocity constraint satisfied: "
   ...     f"{verification.velocity_result.feasible}"
   ... )
   Maximum-velocity constraint satisfied: True
   >>> print(
   ...     "Critical pressure junction: "
   ...     f"{verification.pressure_result.critical_component}"
   ... )
   Critical pressure junction: J1
   >>> print(
   ...     "Critical velocity pipe: "
   ...     f"{verification.velocity_result.critical_component}"
   ... )
   Critical velocity pipe: P1
   >>> assert verification.feasible
   >>> assert verification.pressure_result.feasible
   >>> assert verification.velocity_result.feasible

The ``True`` results show that the candidate design satisfies both the
minimum-pressure and maximum-velocity requirements for this scenario.
The critical component outputs identify where the governing pressure
and velocity values occurred.

Numerical tolerances
--------------------

Floating-point simulation results can differ from an engineering
constraint by a very small numerical amount. Optional tolerances can
therefore be applied at the pressure and velocity boundaries.

A junction-pressure observation is compliant when::

   pressure >= minimum_pressure_m - pressure_tolerance_m

A pipe-velocity observation is compliant when::

   abs(velocity) <= maximum_velocity_mps + velocity_tolerance_mps

Both tolerances must be finite and non-negative. Their default value is
``0.0``, which preserves strict comparison behaviour. Tolerances should
be selected only to accommodate insignificant numerical variation and
should not be used to conceal meaningful hydraulic constraint
violations.

The selected tolerance values are recorded in the verification audit.
For batch assessments, they are also recorded in every summary row and
included in ``configuration_hash``. Experiments using different
tolerances therefore receive different configuration identities.

Checking expectations
---------------------

For routine analysis, verification results can be checked directly using
simple assertions, as demonstrated in the doctest above. This keeps the
workflow focused on whether a candidate design satisfies the hydraulic
pressure, velocity and pump-operating requirements.

Returned information
--------------------

``run_design_verification`` returns three objects.

``verification``
   A structured result containing the pressure assessment, velocity
   assessment, pump-curve audit, simulator error code and overall
   feasibility result.

``hydraulic_results``
   The raw hydraulic simulation results returned by WNTR.

``audit``
   A dictionary recording the applied design, hydraulic scenario,
   simulator, engineering limits, assessed components and pump-curve
   audit.

Pressure assessment
-------------------

Pressure requirements are applied to demand junctions. Reservoirs and
tanks are excluded from the minimum-pressure assessment.

The pressure result reports:

* the minimum simulated pressure;
* the pressure-compliance percentage;
* whether the required compliance was achieved;
* the critical junction; and
* the critical simulation time.

Velocity assessment
-------------------

Velocity requirements are applied to pipes. Pumps and valves are
excluded from the pipe-velocity assessment.

Absolute velocity is used so that reverse flow does not conceal a
velocity-limit exceedance.

The velocity result reports:

* the maximum absolute pipe velocity;
* the velocity-compliance percentage;
* whether the required compliance was achieved;
* the critical pipe; and
* the critical simulation time.

Pump-curve audit
----------------

The pump audit evaluates active head-pump flow observations against the
maximum flow represented by each pump curve.

When pump-speed information is available, the represented curve limit
is adjusted using the simulated or configured operating speed.

A head pump fails the audit when an active flow exceeds its adjusted
curve-domain limit. A head pump that cannot be evaluated does not
silently pass the audit.

The pump audit checks whether simulated flow remains within the
represented curve domain. It does not assess pump efficiency, energy
consumption, cavitation, net positive suction head or manufacturer
selection requirements.


Batch verification
------------------

``run_verification_batch`` evaluates every requested combination of
pipe design, hydraulic scenario and simulator. It returns a summary
``pandas.DataFrame`` and a dictionary that can optionally retain the
hydraulic results from successful experiments.

For example:

.. code-block:: python

   from wntr.extensions.design_verification import (
       run_verification_batch,
   )

   summary, hydraulic_results = run_verification_batch(
       wn=wn,
       scenarios=[
           baseline_scenario,
           peak_demand_scenario,
       ],
       designs=[
           None,
           candidate_design,
       ],
       simulators=(
           "WNTRSimulator",
           "EpanetSimulator",
       ),
       minimum_pressure_m=15.0,
       maximum_velocity_mps=2.5,
       required_compliance_pct=100.0,
       pressure_tolerance_m=1.0e-6,
       velocity_tolerance_mps=1.0e-8,
       continue_on_error=True,
       retain_hydraulic_results=False,
   )

   print(summary)

Using ``None`` in ``designs`` assesses the unchanged baseline network.
When ``designs`` is omitted, only the baseline network is assessed.

Each batch row contains an ``experiment_id``, ``network_hash`` and
``configuration_hash``. The ``network_hash`` is a deterministic
fingerprint of the serialized input water-network model. The
``configuration_hash`` includes that network identity together with
the design, scenario, simulator, constraint limits, compliance
requirement and numerical tolerances. Consequently,
otherwise identical experiments on different network models receive
different configuration hashes. The summary also records hydraulic
feasibility, critical pressure and velocity information, pump
diagnostics and any execution failure.

When ``continue_on_error=True``, a failure during configuration
preparation, hydraulic simulation or result processing is recorded as
a failed row and the remaining combinations continue to run. If
configuration preparation fails before a hash can be generated, the
row uses ``unavailable`` for ``configuration_hash`` and an
``experiment_id`` ending in ``-unavailable``. When
``continue_on_error=False``, the first experiment failure is raised
immediately.

Setting ``retain_hydraulic_results=True`` stores the hydraulic result
object for each successful experiment in the returned dictionary,
indexed by ``experiment_id``. Retaining results can require substantial
memory for large networks, long simulations or many experiment
combinations.

Pump feasibility in batch summaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``pump_feasible`` field has three possible meanings:

* ``True`` means that one or more head pumps were present and all
  evaluated pumps remained within the represented curve domain.
* ``False`` means that one or more head pumps were present and at least
  one pump exceeded its represented curve domain or could not be
  evaluated safely.
* A missing value with ``head_pumps_in_network`` equal to zero means
  that the network contained no head pumps to assess.

A missing ``pump_feasible`` value together with missing pump-count
fields normally indicates that the experiment failed before a complete
pump audit could be produced.

Additional pump-summary fields include
``head_pumps_evaluable``, ``all_head_pumps_evaluable``,
``number_of_pumps_exceeding_curves``,
``total_curve_exceedance_observations``, ``governing_pump_name`` and
``maximum_pump_flow_ratio``.

Protection of the original network
----------------------------------

Pipe-diameter changes and WNTR time and hydraulic simulation options are applied
to independent network copies. The original ``WaterNetworkModel`` supplied to
``run_design_verification`` is therefore preserved.

Verification selects junction-pressure and pipe-velocity results using
WNTR's junction and pipe name lists. WNTR's network registry provides
unique node and link names. Missing required result columns cause the
corresponding pandas column selection to fail. Extra result columns for
reservoirs, tanks, pumps, or valves are permitted and are excluded from
the corresponding junction-pressure and pipe-velocity assessments.

Limitations
-----------

Verification results depend on the quality and completeness of the
network model, hydraulic options, demand assumptions, pump curves and
simulation convergence. Existing network controls can influence the
hydraulic simulation, but controls are not modified or parameterized by
the design-verification extension.

Pressure and velocity limits are supplied by the user. Default values
are not intended to replace applicable utility standards, engineering
codes or regulatory requirements.

The extension verifies simulated hydraulic behaviour. It does not
certify a design for construction or operation.
