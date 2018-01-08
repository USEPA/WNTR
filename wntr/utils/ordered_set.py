import sys
if sys.version_info.major == 2:
    from collections import MutableSet
else:
    from collections.abc import MutableSet
from collections import OrderedDict

class OrderedSet(MutableSet):
    def __init__(self, iterable=None):
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
        self._data[value] = None

    def discard(self, value):
        self._data.pop(value, None)

    def update(self, iterable):
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