.. raw:: latex

    \clearpage

.. _getting_started:

Getting started
======================================

To start using WNTR, open a Python console or IDE like Spyder and import the package::

	import wntr	

WNTR comes with a simple `getting started example <https://github.com/USEPA/WNTR/blob/main/examples/getting_started.py>`_, 
shown below, that uses the `EPANET Example Network 3 (Net3) INP file <https://github.com/USEPA/WNTR/blob/main/examples/networks/Net3.inp>`_.

This example demonstrates how to:

* Import WNTR
* Generate a water network model 
* Simulate hydraulics
* Plot simulation results

.. literalinclude:: ../examples/getting_started.py

Additional examples of Python code snippets are included throughout the WNTR documentation. The examples provided in the documentation assume
that a user has experience using EPANET (https://www.epa.gov/water-research/epanet) and Python (https://www.python.org/), 
including the ability to install and use additional Python packages, such as those listed in :ref:`requirements`.

See :ref:`examples` for more information on downloading and running examples.
