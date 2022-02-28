.. raw:: latex

    \clearpage

.. _advanced_simulation:

Advanced simulation techniques
===============================

This section describes several advanced simulation techniques using WNTR.


.. _stochastic_simulation:

Stochastic simulation
-------------------------------

In contrast to deterministic or enumeration of every possible scenario, 
stochastic simulations is often used to evaluate an ensemble of hydraulic and/or water quality 
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
    >>> selected_pipes = list(np.random.choice(pipe_names, N, replace=False, p=failure_probability))
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
Note that the EPANET 2.0 library was not written to be "thread-safe" (i.e., it does not allow simultaneous use of the library by multiple threads).  
For that reason, the EpanetSimulator must use EPANET 2.2 (which is the default).
The first step is to load the Python packages that are needed for this example and create a water network model.

.. doctest::
    :hide:

    >>> import wntr
    >>> try:
    ...    wn = wntr.network.model.WaterNetworkModel('../examples/networks/Net3.inp')
    ... except:
    ...    wn = wntr.network.model.WaterNetworkModel('examples/networks/Net3.inp')

.. doctest::

    >>> import threading
    >>> import copy
    >>> import numpy as np
    >>> import wntr # doctest: +SKIP

    >>> wn = wntr.network.model.WaterNetworkModel('networks/Net3.inp') # doctest: +SKIP

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

* Get the variables values.  This returns the values for :math:`u` and :math:`v`, which were both initialized to be 1.

* Solve the system of equations and return the solution.

* Add the solution back to the variables values.

* Load the variable values back into the model.

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
