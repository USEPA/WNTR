.. raw:: latex

    \clearpage

.. _advanced_simulation:

Advanced simulation techniques
===============================

This section describes several advanced simulation techniques using WNTR. These techniques include
stochastic simulation, multiple processors, and WNTR's customized algebraic modeling language (AML).


.. _stochastic_simulation:

Stochastic simulation
-------------------------------

In contrast to deterministic or enumeration of every possible scenario, 
stochastic simulation is often used to evaluate an ensemble of hydraulic and/or water quality 
scenarios that are defined using failure probabilities or distributions.  
For disaster scenarios, the location, duration, and severity of different types of incidents
can often be drawn from distributions and included in the simulation in a stochastic manner.
Distributions can be a function of component properties (i.e., age, material) or 
based on engineering standards.
Fragility curves are a common way to include stochasticity in the damage 
state on a component, as described in the Section on :ref:`fragility_curves`.

The Python packages NumPy and SciPy include statistical distributions and random selection methods that can be used for stochastic
simulations.  
For example, the following code uses the NumPy method ``random.choice`` to select two unique pipes from a list of four pipes
based on a failure probability of each pipe.  This information can be used within WNTR to simulate stochastic pipe failure. 

.. doctest::
    :hide:

    >>> import numpy as np
    >>> np.random.seed(12343)
		
.. doctest::

    >>> import numpy as np # doctest: +SKIP
	
    >>> pipe_names = ['pipe1', 'pipe2', 'pipe3', 'pipe4']
    >>> failure_probability = [0.10, 0.20, 0.30, 0.40]
    >>> N = 2
    >>> selected_pipes = list(np.random.choice(pipe_names, N, replace=False, 
    ...     p=failure_probability))
    >>> print(selected_pipes) # doctest: +SKIP
    ['pipe2', 'pipe3']
	

A `stochastic simulation example <https://github.com/USEPA/WNTR/blob/main/examples/stochastic_simulation.py>`_ provided with WNTR runs multiple realizations 
of a pipe leak scenario where the location and duration are drawn from probability 
distributions.

.. _multi_processing:

Multiple processors
------------------------
Since individual disaster scenarios are typically independent, they can be simulated separately.
This independence allows for parallelization and the use of multiple processors, which can significantly reduce the time it takes to run an analysis.
Many different parallelization methods and packages are available to Python users.
The user's operating system and hardware will determine which packages can be used.
Some examples include the multiprocessing Python package, the threading Python package, and Message Passing Interface (MPI) libraries.

Because the threading Python package works with Windows, Linux, and Mac OS X operating systems, it is used in the examples below.
Threads are a "lightweight" method of parallel processing. This means that
the interpreter process is shared among threads, and libraries are only loaded once. 
For more details on how to use threading, see the threading module in 
the standard Python library documentation.

The following example shows how to use the EpanetSimulator in a multi-threaded manner.
The WNTRSimulator can also be used in a similar way. 
Note that the EPANET 2.00.12 library was not written to be "thread-safe" (i.e., it does not allow simultaneous use of the library by multiple threads).  
For that reason, the EpanetSimulator must use EPANET 2.2 (which is the default).
The first step is to load the Python packages that are needed for this example and create a water network model.

.. doctest::

    >>> import threading
    >>> import copy
    >>> import numpy as np
    >>> import wntr

    >>> wn = wntr.network.model.WaterNetworkModel('Net3')

In order to execute a thread, it is necessary to create a function that will perform the actual work.
In this example, a simple function called ``run_epanet`` is created that accepts a water network model,
a name for the model, and a dictionary which contains results.

Because threads do not return a value, the simulation results need to be stored in a mutable object (such as a dictionary or list) that is contained
by the main process.  For this reason, the results from each simulation (called res) are saved to the results dictionary 
which is passed to the run_epanet function as an input.

.. doctest::

    >>> def run_epanet(wn, name, results):
    ...     """Run the EPANET simulator on a water network and store results."""
    ...     sim = wntr.sim.EpanetSimulator(wn)
    ...     res = sim.run_sim(name, version=2.2)
    ...     results[name] = res

The example code below runs five simulations in a multi-threaded manner.
To make each simulation different, the simulation duration is changed for each new simulation.
In practice, the differences would reflect unique conditions for each resilience scenario.

For each simulation, the water network model must be a unique model object to avoid thread conflicts.
This can be accomplished by either creating a new water network model or by copying an existing water network model using ``copy.deepcopy`` method (as shown below).
This is critical when using the WNTRSimulator, as temporary data is stored within the model as the simulation progresses.

The results are stored in the ``results`` dictionary with keys that indicate the thread number (i.e., '0', '1', '2', '3', '4').
Once the threads are created using ``threading.Thread``, they are appended to a list.  
Each thread is started using the ``start`` method and then joined, or completed, using the ``join`` method.

.. doctest::

    >>> num_threads = 5
    >>> results = dict()
    >>> threads = list()
    >>> for i in range(num_threads):
    ...     wn_thread = copy.deepcopy(wn)
    ...     wn_thread.options.time.duration = 86400 + i * 86400
    ...     t = threading.Thread(target=run_epanet, args=(wn_thread, str(i), results))
    ...     threads.append(t)
    >>> for t in threads:
    ...     t.start()
    >>> for t in threads:
    ...     t.join()

When the above example is executed, it runs approximately twice as fast as it does when executed sequentially.
The `test code for threading <https://github.com/USEPA/WNTR/blob/main/wntr/tests/test_sim_performance.py>`_ (see the ``test_Net6_thread_performance`` class) 
includes additional detail on threading.


.. _wntr_aml:

Customized models with WNTR's AML
-------------------------------------------

WNTR has a custom algebraic modeling language (AML) that is used to define the WNTRSimulator's hydraulic model. 
This AML is used for
efficient evaluation of constraint residuals and derivatives. WNTR's
AML drastically simplifies the implementation, maintenance,
modification, and customization of hydraulic models by defining
parameters, variables, and constraints in a natural way. 

The AML also allows the user to customize parameters, variables, and constraints 
by modifying the AML model that defines the WNTRSimulator's hydraulic model. 
For example, this functionality could be used to test out new valve options or demand models.

The example below illustrates the use of WNTR's AML on a simple set of nonlinear equations.

.. math::

   v - u^{2} = 0 \\
   v - u - 1 = 0

The following code is used to create a model (m) of these equations using WNTR's AML.  
The :math:`u` and :math:`v` variables are both initialized to a value of 1.
   
.. doctest::

   >>> from wntr.sim import aml
   
   >>> m = aml.Model()
   >>> m.u = aml.Var(1.0)
   >>> m.v = aml.Var(1.0)
   >>> m.c1 = aml.Constraint(m.v - m.u**2)
   >>> m.c2 = aml.Constraint(m.v - m.u - 1)

Before evaluating or solving the model, the :func:`~wntr.sim.aml.aml.Model.set_structure` must be called:

.. doctest::

   >>> m.set_structure()
   
The model can then be used to evaluate the constraint residuals and the Jacobian. 
The methods :func:`~wntr.sim.aml.aml.Model.evaluate_residuals` and
:func:`~wntr.sim.aml.aml.Model.evaluate_jacobian` return a NumPy array
and a SciPy compressed sparse row (CSR) matrix, respectively. 
The values that are stored in the Jacobian sparse matrix can also be loaded into a NumPy array.

.. doctest::

   >>> m.evaluate_residuals() # doctest: +SKIP
   array([ 0., -1.])
   >>> m.evaluate_jacobian() # doctest: +SKIP
   <2x2 sparse matrix of type '<class 'numpy.float64'>'
	with 4 stored elements in Compressed Sparse Row format>
   >>> m.evaluate_jacobian().toarray() # doctest: +SKIP
   array([[-2.,  1.],
          [-1.,  1.]])


The SciPy method ``sparse.linalg.spsolve`` can be used to solve the system of equations 
:math:`Ax=b`, where 
:math:`A` is the Jacobian of the model, 
:math:`b` is the residual of the model, and 
:math:`x` is the solution to the system of equations.

* Get the variables' values.  This returns the values for :math:`u` and :math:`v`, which were both initialized to be 1.

* Solve the system of equations and return the solution.

* Add the solution back to the variables' values.

* Load the variables' values back into the model.

* Evaluate the residuals of the model.  If the maximum absolute value of the residuals is too high, the solve can be repeated.


.. doctest::

   >>> from scipy.sparse.linalg import spsolve
   
   >>> var_values = m.get_x()
   >>> x = spsolve(m.evaluate_jacobian(), -m.evaluate_residuals())
   >>> var_values = var_values + x
   >>> m.load_var_values_from_x(var_values)
   >>> m.evaluate_residuals() # doctest: +SKIP
   array([-1., 0.])

WNTR includes an implementation of Newton's Method with a line search
which can also be used to solve the set of equations.
This is the default solver for the WNTRSimulator's hydraulic model. 
This method repeats a Newton step until the maximum residual is less than a user 
specified tolerance (set to 1*10 :sup:`-6` by default).
The method ``opt.solve`` returns a tuple which includes the solver status (converged or error).
The solution for :math:`u` and :math:`v` is then returned and printed to four significant digits.

.. doctest::

   >>> from wntr.sim.solvers import NewtonSolver
   
   >>> ns = NewtonSolver()
   >>> solver_status = ns.solve(m)
   >>> np.round(m.u.value,4)
   1.618
   >>> np.round(m.v.value,4)
   2.618

Building MSX models
-------------------

The following two examples illustrate how to build :class:`~wntr.msx.model.MsxModel` objects in WNTR.
See :ref:`jupyter_notebooks` for an example on multispecies analysis.

.. _msx_example1_lead:

Plumbosolvency of lead
^^^^^^^^^^^^^^^^^^^^^^

The following example builds the plumbosolvency of lead model 
described in :cite:p:`bwms20`. The model represents plumbosolvency 
in lead pipes within a dwelling.
The MSX model is built without a specific water network model in mind.

Model development starts by defining the model
name, 
title, 
description, and 
reference.

.. doctest::

    >>> import wntr.msx
    >>> msx = wntr.msx.MsxModel()
    >>> msx.name = "lead_ppm"
    >>> msx.title = "Lead Plumbosolvency Model (from Burkhardt et al 2020)"
    >>> msx.desc = "Parameters for EPA HPS Simulator Model"
    >>> msx.references.append(
    ... """J. B. Burkhardt, et al. (2020) https://doi.org/10.1061/(asce)wr.1943-5452.0001304"""
    ... )
    >>> msx
    MsxModel(name='lead_ppm')

Model options are added as follows:

.. doctest::

    >>> msx.options = {
    ... "report": {
    ...     "species": {"PB2": "YES"},
    ...     "species_precision": {"PB2": 5},
    ...     "nodes": "all",
    ...     "links": "all",
    ... },
    ... "timestep": 1,
    ... "area_units": "M2",
    ... "rate_units": "SEC",
    ... "rtol": 1e-08,
    ... "atol": 1e-08,
    ... }

There is only one species defined in this model, which is dissolved lead.

========================  ===============  =================================  ========================
Name                      Type             Units                              Note
------------------------  ---------------  ---------------------------------  ------------------------
:math:`Pb`                bulk species     :math:`\mathrm{μg}_\mathrm{(Pb)}`  dissolved lead
========================  ===============  =================================  ========================

The species is added to the MsxModel using the using the 
:meth:`~wntr.msx.model.MsxModel.add_species` method.
This method adds the new species to the model and also return a copy of the new species object.

.. doctest::

    >>> msx.add_species(name="PB2", species_type='bulk', units="ug", note="dissolved lead (Pb)")
    Species(name='PB2', species_type='BULK', units='ug', atol=None, rtol=None, note='dissolved lead (Pb)')


The new species can be accessed by using the item's name and indexing on the model's 
:attr:`~wntr.msx.model.MsxModel.reaction_system` attribute.

    >>> PB2 = msx.reaction_system['PB2']
    >>> PB2
    Species(name='PB2', species_type='BULK', units='ug', atol=None, rtol=None, note='dissolved lead (Pb)')

The model also includes two constants and one parameter.

===============  ===============  ===============  =================================  ========================
Type             Name             Value            Units                              Note
---------------  ---------------  ---------------  ---------------------------------  ------------------------
constant         :math:`M`        0.117            :math:`\mathrm{μg~m^{-2}~s^{-1}}`  desorption rate
constant         :math:`E`        140.0            :math:`\mathrm{μg~L^{-1}}`         saturation level
parameter        :math:`F`        0                `flag`                             is pipe made of lead?
===============  ===============  ===============  =================================  ========================

These are added to the MsxModel using the using the 
:meth:`~wntr.msx.model.MsxModel.add_constant` and 
:meth:`~wntr.msx.model.MsxModel.add_parameter` methods.
methods.

.. doctest::

    >>> msx.add_constant("M", value=0.117, note="Desorption rate (ug/m^2/s)", units="ug * m^(-2) * s^(-1)")
    Constant(name='M', value=0.117, units='ug * m^(-2) * s^(-1)', note='Desorption rate (ug/m^2/s)')
    >>> msx.add_constant("E", value=140.0, note="saturation/plumbosolvency level (ug/L)", units="ug/L")
    Constant(name='E', value=140.0, units='ug/L', note='saturation/plumbosolvency level (ug/L)')
    >>> msx.add_parameter("F", global_value=0, note="determines which pipes are made of lead")
    Parameter(name='F', global_value=0.0, note='determines which pipes are made of lead')

If the value of one of these needs to be modified, then it can be accessed and modified as an object
in the same manner as other WNTR objects.

.. doctest::

  >>> M = msx.reaction_system.constants['M']
  >>> M.value = 0.118
  >>> M
  Constant(name='M', value=0.118, units='ug * m^(-2) * s^(-1)', note='Desorption rate (ug/m^2/s)')


Note that all models must include both pipe and tank reactions.
Since the model only has reactions within 
pipes, tank reactions need to be unchanging. 
The system of equations defined as follows:

.. math::

    \frac{d}{dt}Pb_p &= F_p \, Av_p \, M \frac{\left( E - Pb_p \right)}{E}, &\quad\text{for all pipes}~p~\text{in network}  \\
    \frac{d}{dt}Pb_t &= 0, & \quad\text{for all tanks}~t~\text{in network}

Note that the pipe reaction has a variable that has not been defined, :math:`Av`;
this variable is a pre-defined hydraulic variable. The list of these variables can be found in 
the EPANET-MSX documentation, and also in the :attr:`~wntr.msx.base.HYDRAULIC_VARIABLES`
documentation. The reactions are defined as follows:

================  ==============  ==========================================================================
Reaction type     Dynamics type   Reaction expression
----------------  --------------  --------------------------------------------------------------------------
pipe              rate            :math:`F \cdot Av \cdot M \cdot \left( E - Pb \right) / E`
tank              rate            :math:`0`
================  ==============  ==========================================================================

The reactions are added to the MsxModel using the :meth:`~wntr.msx.model.MsxModel.add_reaction`
method.

.. doctest::

    >>> msx.add_reaction("PB2", "pipe", "RATE", expression="F * Av * M * (E - PB2) / E")
    Reaction(species_name='PB2', expression_type='RATE', expression='F * Av * M * (E - PB2) / E')


If the species is saved as an object, as was done above, then it can be passed instead of the species name.

.. doctest::

    >>> msx.add_reaction(PB2, "tank", "rate", expression="0")
    Reaction(species_name='PB2', expression_type='RATE', expression='0')


Arsenic oxidation and adsorption
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example models monochloramine oxidation of arsenite/arsenate and wall
adsorption/desorption, as given in section 3 of the EPANET-MSX user manual :cite:p:`shang2023`.

The system of equations for the reaction in pipes is given in Eq. (2.4) through (2.7)
in :cite:p:`shang2023`. This is a simplified model, taken from :cite:p:`gscl94`. 

.. math::

    \frac{d}{dt}{(\mathsf{As}^\mathrm{III})} &= -k_a ~ {(\mathsf{As}^\mathrm{III})} ~ {(\mathsf{NH_2Cl})} \\
    \frac{d}{dt}{(\mathsf{As}^\mathrm{V})}   &=  k_a ~ {(\mathsf{As}^\mathrm{III})} ~ {(\mathsf{NH_2CL})} - Av \left( k_1 \left(S_\max - {(\mathsf{As}^\mathrm{V}_s)} \right) {(\mathsf{As}^\mathrm{V})} - k_2 ~ {(\mathsf{As}^\mathrm{V}_s)} \right) \\
    \frac{d}{dt}{(\mathsf{NH_2Cl})}          &= -k_b ~ {(\mathsf{NH_2Cl})} \\
    {(\mathsf{As}^\mathrm{V}_s)}            &= \frac{k_s ~ S_\max ~ {(\mathsf{As}^\mathrm{V})}}{1 + k_s {(\mathsf{As}^\mathrm{V})}}


where the various species, coefficients, and expressions are described in the tables below.


.. list-table:: Options
    :header-rows: 1
    :widths: 3 3 10

    * - Option
      - Code
      - Description
    * - Rate units
      - "HR"
      - :math:`\mathrm{h}^{-1}`
    * - Area units
      - "M2"
      - :math:`\mathrm{m}^2`


.. list-table:: Species
    :header-rows: 1
    :widths: 2 2 2 3 4 6

    * - Name
      - Type
      - Value
      - Symbol
      - Units
      - Note
    * - AS3
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{III}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenite
    * - AS5
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{V}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenate
    * - AStot
      - Bulk
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{tot}}`
      - :math:`\require{upgreek}\upmu\mathrm{g~L^{-1}}`
      - dissolved arsenic (total)
    * - NH2CL
      - Bulk
      - "MG"
      - :math:`{\mathsf{NH_2Cl}}`
      - :math:`\mathrm{mg~L^{-1}}`
      - dissolved monochloramine
    * - AS5s
      - Wall
      - "UG"
      - :math:`{\mathsf{As}^\mathrm{V}_{s}}`
      - :math:`\require{upgreek}\upmu\mathrm{g}~\mathrm{m}^{-2}`
      - adsorped arsenate (surface)


.. list-table:: Coefficients
    :header-rows: 1
    :widths: 2 2 2 3 4 6

    * - Name
      - Type
      - Value
      - Symbol
      - Units
      - Note
    * - Ka
      - Const
      - :math:`10`
      - :math:`k_a`
      - :math:`\mathrm{mg}^{-1}_{\left(\mathsf{NH_2Cl}\right)}~\mathrm{h}^{-1}`
      - arsenite oxidation
    * - Kb
      - Const
      - :math:`0.1`
      - :math:`k_b`
      - :math:`\mathrm{h}^{-1}`
      - chloromine decay
    * - K1
      - Const
      - :math:`5.0`
      - :math:`k_1`
      - :math:`\require{upgreek}\textrm{L}~\upmu\mathrm{g}^{-1}_{\left(\mathsf{As}^\mathrm{V}\right)}~\mathrm{h}^{-1}`
      - arsenate adsorption
    * - K2
      - Const
      - :math:`1.0`
      - :math:`k_2`
      - :math:`\textrm{L}~\mathrm{h}^{-1}`
      - arsenate desorption
    * - Smax
      - Const
      - :math:`50.0`
      - :math:`S_{\max}`
      - :math:`\require{upgreek}\upmu\mathrm{g}_{\left(\mathsf{As}^\mathrm{V}\right)}~\mathrm{m}^{-2}`
      - arsenate adsorption limit


.. list-table:: Other terms
    :header-rows: 1
    :widths: 3 3 2 3 10

    * - Name
      - Symbol
      - Expression
      - Units
      - Note
    * - Ks
      - :math:`k_s`
      - :math:`{k_1}/{k_2}`
      - :math:`\require{upgreek}\upmu\mathrm{g}^{-1}_{\left(\mathsf{As}^\mathrm{V}\right)}`
      - equilibrium adsorption coefficient 


.. list-table:: Pipe reactions
    :header-rows: 1
    :widths: 3 3 16

    * - Species
      - Type
      - Expression
    * - AS3
      - Rate 
      - :math:`-k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - AS5
      - Rate
      - :math:`k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}} -Av \left( k_1 \left(S_{\max}-{\mathsf{As}^\mathrm{V}_{s}} \right) {\mathsf{As}^\mathrm{V}} - k_2 \, {\mathsf{As}^\mathrm{V}_{s}} \right)`
    * - NH2CL
      - Rate
      - :math:`-k_b \, {\mathsf{NH_2Cl}}`
    * - AStot
      - Formula
      - :math:`{\mathsf{As}^\mathrm{III}} + {\mathsf{As}^\mathrm{V}}`
    * - AS5s
      - Equil
      - :math:`k_s \, S_{\max} \frac{{\mathsf{As}^\mathrm{V}}}{1 + k_s \, {\mathsf{As}^\mathrm{V}}} - {\mathsf{As}^\mathrm{V}_{s}}`


.. list-table:: Tank reactions
    :header-rows: 1
    :widths: 3 3 16

    * - Species
      - Type
      - Expression
    * - AS3
      - Rate
      - :math:`-k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - AS5
      - Rate
      - :math:`k_a \, {\mathsf{As}^\mathrm{III}} \, {\mathsf{NH_2Cl}}`
    * - NH2CL
      - Rate
      - :math:`-k_b \, {\mathsf{NH_2Cl}}`
    * - AStot
      - Formula
      - :math:`{\mathsf{As}^\mathrm{III}} + {\mathsf{As}^\mathrm{V}}`
    * - AS5s
      - Equil
      - :math:`0` (`not present in tanks`)


The model is created in WTNR as shown below.

.. doctest::

    >>> msx = wntr.msx.MsxModel()
    >>> msx.name = "arsenic_chloramine"
    >>> msx.title = "Arsenic Oxidation/Adsorption Example"

    >>> AS3 = msx.add_species(name="AS3", species_type="BULK", units="UG", note="Dissolved arsenite")
    >>> AS5 = msx.add_species(name="AS5", species_type="BULK", units="UG", note="Dissolved arsenate")
    >>> AStot = msx.add_species(name="AStot", species_type="BULK", units="UG", 
    ...     note="Total dissolved arsenic")
    >>> AS5s = msx.add_species(name="AS5s", species_type="WALL", units="UG", note="Adsorbed arsenate")
    >>> NH2CL = msx.add_species(name="NH2CL", species_type="BULK", units="MG", note="Monochloramine")

    >>> Ka = msx.add_constant("Ka", 10.0, units="1 / (MG * HR)", note="Arsenite oxidation rate coeff")
    >>> Kb = msx.add_constant("Kb", 0.1, units="1 / HR", note="Monochloramine decay rate coeff")
    >>> K1 = msx.add_constant("K1", 5.0, units="M^3 / (UG * HR)", note="Arsenate adsorption coeff")
    >>> K2 = msx.add_constant("K2", 1.0, units="1 / HR", note="Arsenate desorption coeff")
    >>> Smax = msx.add_constant("Smax", 50.0, units="UG / M^2", note="Arsenate adsorption limit")
    
    >>> Ks = msx.add_term(name="Ks", expression="K1/K2", note="Equil. adsorption coeff")

    >>> _ = msx.add_reaction(species_name="AS3", reaction_type="pipes", expression_type="rate", 
    ...     expression="-Ka*AS3*NH2CL", note="Arsenite oxidation")
    >>> _ = msx.add_reaction("AS5", "pipes", "rate", "Ka*AS3*NH2CL - Av*(K1*(Smax-AS5s)*AS5 - K2*AS5s)", 
    ...     note="Arsenate production less adsorption")
    >>> _ = msx.add_reaction(
    ...     species_name="NH2CL", reaction_type="pipes", expression_type="rate", expression="-Kb*NH2CL", 
    ...     note="Monochloramine decay")
    >>> _ = msx.add_reaction("AS5s", "pipe", "equil", "Ks*Smax*AS5/(1+Ks*AS5) - AS5s", 
    ...     note="Arsenate adsorption")
    >>> _ = msx.add_reaction(species_name="AStot", reaction_type="pipes", expression_type="formula", 
    ...     expression="AS3 + AS5", note="Total arsenic")
    >>> _ = msx.add_reaction(species_name="AS3", reaction_type="tank", expression_type="rate", 
    ...     expression="-Ka*AS3*NH2CL", note="Arsenite oxidation")
    >>> _ = msx.add_reaction(species_name="AS5", reaction_type="tank", expression_type="rate", 
    ...     expression="Ka*AS3*NH2CL", note="Arsenate production")
    >>> _ = msx.add_reaction(species_name="NH2CL", reaction_type="tank", expression_type="rate", 
    ...     expression="-Kb*NH2CL", note="Monochloramine decay")
    >>> _ = msx.add_reaction(species_name="AStot", reaction_type="tanks", expression_type="formula", 
    ...     expression="AS3 + AS5", note="Total arsenic")

    >>> msx.options.area_units = "M2"
    >>> msx.options.rate_units = "HR"
    >>> msx.options.rtol = 0.001
    >>> msx.options.atol = 0.0001
