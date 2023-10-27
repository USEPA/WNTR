# coding: utf-8
"""Decorators for use with enum classes.
"""

from enum import Enum
from typing import Union
import functools

def add_get(cls=None, *, prefix=None, abbrev=False, allow_none=True):
    """Decorator that will add a ``get()`` classmethod to an enum class.

    Parameters
    ----------
    prefix : str, optional
        A prefix to strip off any string values passed in, by default None
    abbrev : bool, optional
        Allow truncating to the first character for checks, by default False
    allow_none : bool, optional
        Allow None to be be passed through without raising error, by default True
    
    Returns
    -------
    class
        the modified class

    Notes
    -----
    The ``get`` method behaves as follows:

    For an integer, the integer value will be used to select the proper member.
    For an :class:`Enum` object, the object's ``name`` will be used, and it will
    be processed as a string. For a string, the method will:
    
    0. if ``allow_none`` is False, then raise a TypeError if the value is None, otherwise
       pass None back to calling function for processing
    1. capitalize the string
    2. remove leading or trailing spaces
    3. convert interior spaces or dashes to underscores
    4. optionally, remove a specified prefix from a string (using ``prefix``, which 
        should have a default assigned by the :func:`wntr.utils.enumtools.add_get` 
        function.)

    It will then try to get the member with the name corresponding to the converted
    string.
    
    5. optionally, if ``abbrev`` is True, then the string will be truncated to the first
        letter, only, after trying to use the full string as passed in. The ``abbrev``
        parameter will have a default value based on how the :func:`~wntr.utils.enumtools.add_get`
        decorator was called on this class.
    
    """
    if prefix is None:
        prefix = ''
    if abbrev is None:
        abbrev = False
    if allow_none is None:
        allow_none = True
    if cls is None:
        return functools.partial(add_get, prefix=prefix, abbrev=abbrev, allow_none=allow_none)

    @functools.wraps(cls)
    def wrap(cls, prefix, abbrev):
        """Perform the decorator action"""

        def get(cls, value: Union[str, int, Enum], prefix='', abbrev=False, allow_none=True):
            """Get the proper enum based on the name or value of the argument.

            See :func:`~wntr.utils.enumtools.add_get` for details on how this function works.
            

            Parameters
            ----------
            value : Union[str, int, Enum]
                the value to be checked, if it is an Enum, then the name will be used
            prefix : str, optional
                a prefix to strip from the beginning of ``value``, default blank or set by decorator
            abbrev : bool, optional
                whether to try a single-letter version of ``value``, default False or set by decorator
            allow_none : bool, optional
                passing None will return None, otherwise will raise TypeError, default True or set by decorator

            Returns
            -------
            Enum
                the enum member that corresponds to the name or value passed in

            Raises
            ------
            TypeError
                if ``value`` is an invalid type
            ValueError
                if ``value`` is invalid

            """
            if value is None and allow_none:
                return None
            elif value is None:
                raise TypeError('A value is mandatory, but got None')
            name = str(value)
            if isinstance(value, cls):
                return value
            elif isinstance(value, int):
                return cls(value)
            elif isinstance(value, str):
                name = value.upper().strip().replace('-', '_').replace(' ', '_')
                if name.startswith(prefix):
                    name = name[len(prefix):]
            elif isinstance(value, Enum):
                name = str(value.name).upper().strip().replace('-', '_').replace(' ', '_')
                if name.startswith(prefix):
                    name = name[len(prefix):]
            else:
                raise TypeError('Invalid type for value: %s'%type(value))
            if abbrev:
                try:
                    return cls[name]
                except KeyError as e:
                    try:
                        return cls[name[0]]
                    except KeyError:
                        raise ValueError(repr(value)) from e
            else:
                try:
                    return cls[name]
                except KeyError as e:
                    raise ValueError(repr(value)) from e
        
        setattr(cls, "get", classmethod(functools.partial(get, prefix=prefix, abbrev=abbrev)))
        return cls

    return wrap(cls, prefix, abbrev)

