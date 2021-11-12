.. raw:: latex

    \clearpage

.. _advanced_simulation:

Advanced simulation techniques
===============================

In addition to the methods which have been described previously, there are many other
ways to use the WNTR toolkit. This section describes several additional, advanced methods
to use WNTR.


.. _stochastic_simulation:

Stochastic simulation
-------------------------------

Stochastic simulations can be used to evaluate an ensemble of hydraulic and/or water quality 
scenarios.  For disaster scenarios, the location, duration, and severity of different types of incidents
can be drawn from distributions and included in the simulation.  
Distributions can be a function of component properties (i.e., age, material) or 
based on engineering standards.
The Python packages NumPy and SciPy include statistical distributions and random selection methods that can be used for stochastic
simulations.  

For example, the following code can be used to select N unique pipes 
based on the failure probability of each pipe.

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
				     
A `stochastic simulation example <https://github.com/USEPA/WNTR/blob/main/examples/stochastic_simulation.py>`_ provided with WNTR runs multiple realizations 
of a pipe leak scenario where the location and duration are drawn from probability 
distributions.


Multiple processors
------------------------
One aspect of stochastic simulation is that it is highly parallelizable; each
realization is an independent simulation that can be modeled separately.
There are many different parallelization methods and packages available to 
python users. Some example tools are: the `multiprocessing` package, MPI libraries,
or using threading.
This section will show an example of how to run the :class:`~wntr.sim.epanet.EpanetSimulator`
in a multi-threaded manner.

Threads are a "lightweight" method of doing parallel processing. This means that
the interpreter process is shared among threads, and, specifically, that libraries
are only loaded once. Because the EPANET 2.0 library is not "thread-safe", threading
only works if the :class:`~wntr.sim.epanet.EpanetSimulator` is run using with the 
argument `version=2.2` (which is the default).

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')

.. doctest::

    >>> import threading
    >>> import time
    >>> import copy
    >>> import wntr # doctest: +SKIP

    >>> wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp') # doctest: +SKIP

The first step is to create a function that will perform the actual work for each thread.
In this example, there will be a simple function that will accept a water network model,
a name for the model and thread, and a dictionary which will contain results.


.. doctest::

    >>> def run_epanet(wn, name, results):
    ...     sim = wntr.sim.EpanetSimulator(wn)
    ...     res = sim.run_sim(name, version=2.2)
    ...     results[name] = res


The threads in the standard Python threading module do return a value. However, because the
threads are lightweight, they can store results in a single mutable object that is contianed
by the main process, such as a dictionary or list, as long as the indices are unique.
For details on how to use threading, see the :class:`threading` module in 
the standard python library documentation.

To test the difference in performance, the simulation can be run sequentially and then in 
parallel.
First, the simulations are run sequentially. To make the results interesting, each simulation
will run for one longer than the previous.

.. doctest::

    >>> results = dict()
    >>> n = 2

    >>> start_time = time.time()
    >>> for i in range(n):
    ...     wn.options.time.duration = 86400 + i * 86400
    ...     run_epanet(wn, 'test-seq-{}'.format(i), results)
    
    >>> print("Sequential run time: %.2f seconds"%(time.time() - start_time)) # doctest: +SKIP
    Sequential run time: 0.07 seconds

    >>> print("Results added: ", results.keys()) # doctest: +SKIP
    Results added:  dict_keys(['test-seq-0', 'test-seq-1'])

    >>> t1 = results['test-seq-0'].node['demand'].index[-1]
    >>> t2 = results['test-seq-1'].node['demand'].index[-1]
    >>> print("Final time step: test-seq-0 = {}, test-seq-1 = {}".format(t1, t2))
    Final time step: test-seq-0 = 86400, test-seq-1 = 172800


The results are executed in 0.7 seconds, and the results show that the last index of the 
results is 1 day for the first simulation and 2 days for the second simulation.

For the parallel simulation, the water network model must be copied into new model objects
to avoid any thread conflicts.

.. doctest::

    >>> threads = list()
    >>> start_time = time.time()
    >>> for i in range(n):
    ...     wn_thread = copy.deepcopy(wn)
    ...     wn_thread.options.time.duration = 86400 + i * 86400
    ...     t = threading.Thread(target=run_epanet, args=(wn_thread, 'test-par-{}'.format(i), results))
    ...     threads.append(t)
    >>> for t in threads:
    ...     t.start()
    >>> for t in threads:
    ...     t.join()

    >>> print("Parallel run time: %.2f seconds"%(time.time()-start_time))  # doctest: +SKIP
    Parallel run time: 0.04 seconds

    >>> print("Results added: ", results.keys()) # doctest: +SKIP
    Results added:  dict_keys(['test-seq-0', 'test-seq-1', 'test-par-0', 'test-par-1'])

    >>> t3 = results['test-par-0'].node['demand'].index[-1]
    >>> t4 = results['test-par-1'].node['demand'].index[-1]
    >>> print("Final time step: test-par-0 = {}, test-par-1 = {}".format(t3, t4))
    Final time step: test-par-0 = 86400, test-par-1 = 172800


After the threads are executed, there are two additional keys that have been added to the 
results dictionary. The execution time was roughly half of the sequential execution time.
The final time step of the results are again 1 and 2 days.

The :class:`~wntr.sim.core.WNTRSimulator` can also be used in this way. Ensuring that the water network model
is either reloaded or copied using deepcopy is critical when using multi-processing
with the :class:`~wntr.sim.core.WNTRSimulator`, as temporary data is stored inside the 
:class:`~wntr.network.model.WaterNetworkModel` in this case.



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
