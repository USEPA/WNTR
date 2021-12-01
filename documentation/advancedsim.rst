.. raw:: latex

    \clearpage

.. _advanced_simulation:

Advanced simulation techniques
===============================

In addition to the methods which have been described previously, WNTR can be used in many other ways. This section describes several advanced simulation techniques.


.. _stochastic_simulation:

Stochastic simulation
-------------------------------

Stochastic simulations can be used to evaluate an ensemble of hydraulic and/or water quality 
scenarios.  
While a "run-all" approach may be useful, or appropriate, in some situations,
for disaster scenarios, the location, duration, and severity of different types of incidents
can often be drawn from distributions and included in the simulation in a stochastic manner.
Distributions can be a function of component properties (i.e., age, material) or 
based on engineering standards.
Fragility curves are a common way to include stochasticity in the damage 
state on a component, as described in the Section on :ref:`fragility_curves`.

The Python packages NumPy and SciPy include statistical distributions and random selection methods that can be used for stochastic
simulations.  
For example, the following code can be used to select N unique pipes 
based on the failure probability of each pipe.  
The ``selected_pipes`` variable will be a list of two pipe names selected based on the failure probabilities.

.. doctest::
    :hide:

    >>> import numpy as np
    >>> np.random.seed(12343)
		
.. doctest::

    >>> import numpy as np # doctest: +SKIP
	
    >>> pipe_names = ['pipe1', 'pipe2', 'pipe3', 'pipe4']
    >>> failure_probability = [0.10, 0.20, 0.30, 0.40]
    >>> N = 2
    >>> selected_pipes = np.random.choice(pipe_names, N, replace=False, 
    ...     p=failure_probability)
				     
This information can be used within WNTR to simulate stochastic pipe failure.
A `stochastic simulation example <https://github.com/USEPA/WNTR/blob/main/examples/stochastic_simulation.py>`_ provided with WNTR runs multiple realizations 
of a pipe leak scenario where the location and duration are drawn from probability 
distributions.

.. _multi_processing:

Multiple processors
------------------------
In order to speed up independent calculations, simulations can be parallelized.
There are many different parallelization methods and packages available to 
Python users, although the operating system and hardware available will determine which packages can be used.
Some examples are the :class:`multiprocessing` package, MPI libraries,
or the :class:`threading` package. 
Because the :class:`threading` package works with almost all systems, it will be used in the examples below.

The example of how to run the :class:`~wntr.sim.epanet.EpanetSimulator`
in a multi-threaded manner.
The :class:`~wntr.sim.core.WNTRSimulator` can also be used in a similar way. 
Threads are a "lightweight" method of parallel processing. This means that
the interpreter process is shared among threads, and, more specifically, that libraries
are only loaded once. 
However, the EPANET 2.0 library was not written to be "thread-safe" -- i.e., it does not allow simultaneous use of the library by multiple threads -- so the :class:`~wntr.sim.epanet.EpanetSimulator` must be run using EPANET 2.2 (which is the default).

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')


The first step is to load the ``threading`` and other packages and load in a network model.
In order to execute a thread, it is necessary to create a function that will perform the actual work.
In this specific example, a simple function (listed below) is created that accepts a water network model,
a name for the model, and a dictionary which will contain results.


.. doctest::

    >>> import threading
    >>> import copy
    >>> import wntr # doctest: +SKIP

    >>> wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp') # doctest: +SKIP

    >>> def run_epanet(wn, name, results):
    ...     """Run the EPANET simulator on a water network."""
    ...     sim = wntr.sim.EpanetSimulator(wn)
    ...     res = sim.run_sim(name, version=2.2)
    ...     results[name] = res


Threads in the standard Python threading module do not return a value; however, because the
threads are lightweight, they can store results in a mutable object, such as a dictionary or list, that is contained
by the main process -- as long as the indices are unique.
For details on how to use threading, see the :class:`threading` module in 
the standard Python library documentation.

The example code below shows how to run different simulations with 
different durations.
The results are stored in the ``results`` dictionary with keys
``parallel-1``, ``parallel-2``, ..., where the number indicates the number of days that were simulated.
Once the threads are created, they are started using the ``start`` method and then joined, or completed, using the ``join`` method.

.. doctest::

    >>> num_threads = 5
    >>> results = dict()
    >>> threads = list()
    >>> for i in range(num_threads):
    ...     wn_thread = copy.deepcopy(wn)
    ...     wn_thread.options.time.duration = 86400 + i * 86400
    ...     t = threading.Thread(target=run_epanet, args=(wn_thread, 'parallel-{}'.format(i), results))
    ...     threads.append(t)
    >>> for t in threads:
    ...     t.start()
    >>> for t in threads:
    ...     t.join()


For the parallel simulation, the water network model must be copied into new model objects
to avoid any thread conflicts.
Ensuring that the water network model
is either reloaded from scratch or copied using ``copy.deepcopy`` is critical when using threading
with the :class:`~wntr.sim.core.WNTRSimulator`, as temporary data is stored inside the 
:class:`~wntr.network.model.WaterNetworkModel` as the simulation progresses.

When the above example is executed, it runs approximately twice as fast as it does when executed sequentially.
The 
`test code for threading <https://github.com/USEPA/WNTR/blob/main/wntr/tests/test_sim_performance.py>`_ (see the ``test_Net6_thread_performance`` class) shows additional detail on threading.


.. _wntr_aml:

Customized models with WNTR's AML
-------------------------------------------

WNTR has a custom algebraic modeling language (AML) that is used for
WNTR's hydraulic model (used in the
:class:`~wntr.sim.core.WNTRSimulator`). This AML is primarily used for
efficient evaluation of constraint residuals and derivatives. WNTR's
AML drastically simplifies the implementation, maintenance,
modification, and customization of hydraulic models. The AML allows
defining variables and constraints in a natural way. For example,
suppose the user wants to solve the following system of nonlinear equations.

.. math::

   y - x^{2} = 0 \\
   y - x - 1 = 0

To create this model using WNTR's AML, the following can be used:
   
.. doctest::

   >>> from wntr.sim import aml
   
   >>> m = aml.Model()
   >>> m.x = aml.Var(1.0)
   >>> m.y = aml.Var(1.0)
   >>> m.c1 = aml.Constraint(m.y - m.x**2)
   >>> m.c2 = aml.Constraint(m.y - m.x - 1)

Before evaluating the constraint residuals or the Jacobian, :func:`~wntr.sim.aml.aml.Model.set_structure` must be called:

.. doctest::

   >>> m.set_structure()
   >>> m.evaluate_residuals() # doctest: +SKIP
   array([ 0., -1.])
   >>> m.evaluate_jacobian()  # doctest: +SKIP
   <2x2 sparse matrix of type '<class 'numpy.float64'>'
	with 4 stored elements in Compressed Sparse Row format>
   >>> m.evaluate_jacobian().toarray() # doctest: +SKIP
   array([[-2.,  1.],
       [-1.,  1.]])

The methods :func:`~wntr.sim.aml.aml.Model.evaluate_residuals` and
:func:`~wntr.sim.aml.aml.Model.evaluate_jacobian` return a NumPy array
and a SciPy sparse CSR matrix, respectively. Variable values can also
be loaded with a NumPy array. For example, a Newton
step (without a line search) would look something like

.. doctest::

   >>> from scipy.sparse.linalg import spsolve
   
   >>> x = m.get_x()
   >>> d = spsolve(m.evaluate_jacobian(), -m.evaluate_residuals())
   >>> x += d
   >>> m.load_var_values_from_x(x)
   >>> m.evaluate_residuals() # doctest: +SKIP
   array([-1., 0.])

WNTR includes an implementation of Newton's Method with a line search
which can solve one of these models.

.. doctest::

   >>> from wntr.sim.solvers import NewtonSolver
   
   >>> opt = NewtonSolver()
   >>> res = opt.solve(m)
   >>> m.x.value # doctest: +SKIP
   1.618033988749989
   >>> m.y.value # doctest: +SKIP
   2.618033988749989
