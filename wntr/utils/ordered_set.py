import sys
from collections.abc import MutableSet
from collections import OrderedDict
from collections.abc import Iterable


class OrderedSet(MutableSet):
    """
    An ordered set.
    """
    def __init__(self, iterable=None):
        """
        Parameters
        ----------
        iterable: Iterable
            An iterable with wich to initialize the set.
        """
        self._data = OrderedDict()
        if iterable is not None:
            self.update(iterable)

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return len(self._data)

    def add(self, value):
        """
        Add an element to the set.

        Parameters
        ----------
        value: object
            The object to be added to the set.
        """
        self._data[value] = None

    def discard(self, value):
        """
        Discard and element from the set.

        Parameters
        ----------
        value: object
            The object to be discarded.
        """
        self._data.pop(value, None)

    def update(self, iterable):
        """
        Update the set with the objects in iterable.

        Parameters
        ----------
        iterable: Iterable
        """
        for i in iterable:
            self.add(i)

    def __repr__(self):
        s = '{'
        for i in self:
            s += str(i)
            s += ', '
        s += '}'
        return s

    def __str__(self):
        return self.__repr__()

    def union(self, iterable):
        ret = OrderedSet(self)
        for i in iterable:
            ret.add(i)
        return ret

    def __sub__(self, other):
        ret = OrderedSet(self)
        for i in other:
            ret.discard(i)
        return ret
