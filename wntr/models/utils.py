from wntr.utils.ordered_set import OrderedDict, OrderedSet
import abc


class ModelUpdater(object):
    def __init__(self):
        self.update_functions = OrderedDict()

    def add(self, obj, attr, func):
        if (obj, attr) not in self.update_functions:
            self.update_functions[(obj, attr)] = OrderedSet()
        self.update_functions[(obj, attr)].add(func)


class Definition(object, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def build(cls, m, wn, updater, index_over=None):
        pass

    @classmethod
    def update(cls, m, wn, updater, obj, attr):
        cls.build(m, wn, updater, index_over=[obj.name])


