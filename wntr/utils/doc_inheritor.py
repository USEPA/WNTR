"""Utilitiy for inheriting docstrings."""

import inspect


class DocInheritor(object):
    def __init__(self, methods):
        self.methods = methods

    def __call__(self, cls):
        mro = inspect.getmro(cls)
        if mro[0] is not cls:
            raise RuntimeError('Unexpected')
        if len(mro) < 2:
            raise ValueError('Cannot determine parent class for {0}'.format(cls))
        parent = mro[1]
        for meth in self.methods:
            if not hasattr(parent, meth):
                raise ValueError('Parent class {0} does not have method {1}'.format(parent, meth))
            setattr(getattr(cls, meth), '__doc__', getattr(parent, meth).__doc__)
        return cls


# Example:
#
# class Foo(object):
#     def __init__(self, x):
#         """
#         Parameters
#         ----------
#         x: float
#         """
#         self.x = x
#
#     def inc(self):
#         """
#         increment x
#         """
#         self.x += 1
#
#
# @DocInheritor({'inc'})
# class Bar(Foo):
#     def inc(self):
#         self.x += 2
