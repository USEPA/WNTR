
.. role:: red

.. raw:: latex

    \clearpage

.. _hello_world:

Hello World
===========================================

**Summary**: "hello_world" is a WNTR extension that demonstrates the file structure of a simple extension. 
See :ref:`contributing` for more information on creating an extension.
   
**Point of contact**: Katherine Klise, https://github.com/kaklise

-----

The Hello World extension contains a single function that returns "Hello World!".

.. doctest::

    >>> import wntr.extensions.hello_world as hello_world
	
    >>> output = hello_world.example_module.example_function()
    >>> print(output)
    Hello World!
