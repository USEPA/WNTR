import sys
from collections import OrderedDict
from aml.expression import Var, Param, create_var, create_param
from aml.component import Constraint, ConditionalConstraint, Objective, create_constraint, create_conditional_constraint, create_objective
from aml.ipopt_model import IpoptModel
if sys.version_info.major == 2:
    from collections import MutableSet, MutableMapping
else:
    from collections.abc import MutableSet, MutableMapping


recursive = False


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

    def add(self, item):
        """
        Add an element
        """
        self._data[item] = None

    def discard(self, item):
        """
        Remove an element. Do not raise an exception if absent.
        """
        self._data.pop(item, default=None)

    def __repr__(self):
        return list(self._data.keys()).__repr__()

    def __str__(self):
        return self.__repr__()

    def update(self, iterable):
        """
        Add items from iterable
        """
        for i in iterable:
            self.add(i)


class _OrderedIndexSet(OrderedSet):
    def add(self, item):
        """
        Add an element
        """
        if item not in self:
            item.index = len(self)
            self._data[item] = None

    def discard(self, item):
        """
        Remove an element. Do not raise an exception if absent.
        """
        if item in self:
            for i in list(self._data.keys())[item.index:]:
                i.index -= 1
            item.index = -1
            self._data.pop(item)


class Model(object):
    """
    A class for creating algebraic models.
    """
    def __init__(self):
        self._vars = _OrderedIndexSet()
        self._cons = _OrderedIndexSet()
        self._model = IpoptModel()

    def __setattr__(self, name, val):
        """
        Override built in __setattr__ so that params, vars, etc. get put in the appropriate dictionary

        Parameters
        ----------
        name: str
            name of the attribute
        val: object
            value of the attribute

        Returns
        -------
        None
        """
        if isinstance(val, Param):
            val.name = name
        elif isinstance(val, Var):
            val.name = name
            self._register_var(val)
        elif isinstance(val, Constraint):
            val.name = name
            self._register_constraint(val)
        elif isinstance(val, VarDict):
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_var(v)
        elif isinstance(val, ParamDict):
            val.name = name
        elif isinstance(val, ConstraintDict):
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_constraint(v)
        elif isinstance(val, Objective):
            print('setting objective on IpoptModel')
            self._model.set_objective(val)
            print('done setting objective on IpoptModel')

        # The __setattr__ of the parent class should always be called so that the attribute actually gets set.
        super(Model, self).__setattr__(name, val)

    def __delattr__(self, name):
        """
        Override built in __delattr__ so that params, vars, etc. get removed from the appropriate dictionary

        Parameters
        ----------
        name: str
            name of the attribute

        Returns
        -------
        None
        """
        # The __delattr__ of the parent class should always be called so that the attribute actually gets removed.
        val = getattr(self, name)
        if isinstance(val, Constraint):
            self._remove_constraint(val)
            val.name = 'None'
        elif isinstance(val, ConstraintDict):
            val.name = 'None'
            val._model = None
            for k, v in val.items():
                self._remove_constraint(v)
        elif isinstance(val, Var):
            self._remove_var(val)
            val.name = 'None'
        elif isinstance(val, VarDict):
            val.name = 'None'
            val._model = None
            for k, v in val.items():
                self._remove_var(v)
        super(Model, self).__delattr__(name)

    def _register_var(self, var):
        self._vars.add(var)
        self._model.add_var(var)

    def _remove_var(self, var):
        self._model.remove_var(var)
        self._vars.remove(var)

    def _register_constraint(self, con):
        self._cons.add(con)
        self._model.add_constraint(con)

    def _remove_constraint(self, con):
        self._model.remove_constraint(con)
        self._cons.remove(con)

    def solve(self):
        self._model.solve()

    def __str__(self):
        tmp = 'cons:\n'
        for con in self._cons:
            tmp += str(con.index)
            tmp += ':   '
            tmp += con.__str__()
            tmp += '\n'
        tmp += '\n'
        tmp += 'vars:\n'
        for var in self._vars:
            tmp += str(var.index)
            tmp += ':   '
            tmp += var.__str__()
            tmp += '\n'
        return tmp


class _NodeDict(MutableMapping):
    def __init__(self, mapping=None):
        self._name = 'None'
        self._data = OrderedDict()

        if mapping is not None:
            self.update(mapping)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = val
        for k, v in self.items():
            v.name = self.name + '[' + str(k) + ']'

    def __delitem__(self, key):
        self._data[key].name = None
        del self._data[key]

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return self._data.__repr__()

    def __setitem__(self, key, val):
        val.name = self.name + '[' + str(key) + ']'
        self._data[key] = val

    def __str__(self):
        return self.__repr__()


class ParamDict(_NodeDict):
    pass


class VarDict(_NodeDict):
    def __init__(self, mapping=None):
        self._model = None
        super(VarDict, self).__init__(mapping)

    def __delitem__(self, key):
        val = self[key]
        if self._model is not None:
            self._model._remove_var(val)
        val.name = None
        del self._data[key]

    def __setitem__(self, key, val):
        self.pop(key, default=None)
        if self._model is not None:
            self._model._register_var(val)
        val.name = self.name + '[' + str(key) + ']'
        self._data[key] = val


class ConstraintDict(_NodeDict):
    def __init__(self, mapping=None):
        self._model = None
        super(ConstraintDict, self).__init__(mapping)

    def __delitem__(self, key):
        val = self[key]
        if self._model is not None:
            self._model._remove_constraint(val)
        val.name = 'None'
        del self._data[key]

    def __setitem__(self, key, val):
        self.pop(key, default=None)
        val.name = self.name + '[' + str(key) + ']'
        if self._model is not None:
            self._model._register_constraint(val)
        self._data[key] = val
