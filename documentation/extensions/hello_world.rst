
.. role:: red

.. raw:: latex

    \clearpage

.. _hello_world:

Hello World
===========================================

.. note:: 
   "hello_world" is a WNTR extension that demonstrates the file structure of a simple extension.
   
The Hello World extension contains a single function that returns "Hello World!".

.. doctest::

    >>> import wntr.extensions.hello_world as hello_world
	
    >>> output = hello_world.example_module.example_function()
    >>> print(output)
    Hello World!
    
See :ref:`contributing` for more information on creating an extension.
