"""Utilities for the WNTRSimulator model."""

from wntr.utils.ordered_set import OrderedDict, OrderedSet
from six import with_metaclass
import abc


class ModelUpdater(object):
    def __init__(self):
        self.update_functions = OrderedDict()

    def add(self, obj, attr, func):
        if (obj, attr) not in self.update_functions:
            self.update_functions[(obj, attr)] = OrderedSet()
        self.update_functions[(obj, attr)].add(func)

    def update(self, m, wn, obj, attr):
        if (obj, attr) in self.update_functions:
            for func in self.update_functions[(obj, attr)]:
                func(m, wn, self, obj, attr)


class Definition(with_metaclass(abc.ABCMeta, object)):
    @classmethod
    @abc.abstractmethod
    def build(cls, m, wn, updater, index_over=None):
        pass

    @classmethod
    def update(cls, m, wn, updater, obj, attr):
        cls.build(m, wn, updater, index_over=[obj.name])


