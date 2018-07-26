import sys
from collections import OrderedDict
from .aml_core import Node, Var, Param, create_var, create_param
from .aml_core import Component, ConstraintBase, Constraint, ConditionalConstraint, Objective, create_constraint, create_conditional_constraint, create_objective
try:
    from .ipopt_model import IpoptModel
    ipopt_available = True
except ImportError:
    ipopt_available = False
from .aml_core import WNTRModel, CSRJacobian
import scipy
if sys.version_info.major == 2:
    from collections import MutableSet
else:
    from collections.abc import MutableSet
from collections import OrderedDict
if sys.version_info.major == 2:
    from collections import MutableMapping
else:
    from collections.abc import MutableMapping


class _OrderedIndexSet(MutableSet):
    def __init__(self, iterable=None):
        self._data = OrderedDict()
        self._reversed = OrderedDict()
        if iterable is not None:
            self.update(iterable)

    def __contains__(self, item):
        return item.name in self._data

    def __iter__(self):
        for name in self._data:
            yield self._reversed[name]

    def __len__(self):
        return len(self._data)

    def add(self, item):
        """
        Add an element
        """
        if item not in self:
            item.index = len(self)
            self._data[item.name] = 1
            self._reversed[item.name] = item
        else:
            self._data[item.name] += 1

    def discard(self, item):
        """
        Remove an element. Do not raise an exception if absent.
        """
        if item in self:
            self._data[item.name] -= 1
            if self._data[item.name] == 0:
                for i in list(self)[item.index:]:
                    i.index -= 1
                item.index = -1
                self._data.pop(item.name)
                self._reversed.pop(item.name)

    def update(self, iterable):
        for i in iterable:
            self.add(i)

    def count(self, item):
        return self._data[item.name]

    def __repr__(self):
        s = '{'
        for i in self:
            s += str(i)
            s += ', '
        s += '}'
        return s

    def __str__(self):
        return self.__repr__()


class Model(object):
    """
    A class for creating algebraic models.
    """
    def __init__(self, model_type='wntr'):
        self._vars = _OrderedIndexSet()
        self._cons = _OrderedIndexSet()
        self._obj = list()
        if model_type.upper() == 'WNTR':
            self._model = WNTRModel()
        elif model_type.upper() == 'IPOPT':
            if not ipopt_available:
                raise ValueError('Ipopt is not available')
            self._model = IpoptModel()
        else:
            raise ValueError('Unrecognized model_type: '+model_type)

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
        if isinstance(val, (Node, Component, _NodeDict)):
            if hasattr(self, name):
                raise ValueError('Model already has a {0} named {1}. If you want to replace the {0}, please remove the existing one first.'.format(type(val), name))

        if isinstance(val, (Node, VarDict, ParamDict)):
            val.name = name
        elif isinstance(val, ConstraintBase):
            val.name = name
            self._register_constraint(val)
        elif isinstance(val, ConstraintDict):
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_constraint(v)
        elif isinstance(val, Objective):
            self._register_objective(val)

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
        if isinstance(val, (Node, VarDict, ParamDict)):
            val.name = 'None'
        elif isinstance(val, ConstraintBase):
            self._remove_constraint(val)
            val.name = 'None'
        elif isinstance(val, ConstraintDict):
            val.name = 'None'
            val._model = None
            for k, v in val.items():
                self._remove_constraint(v)
        elif val is self._obj:
            self._remove_objective()
        super(Model, self).__delattr__(name)

    def _register_var(self, var):
        if var not in self._vars:
            self._vars.add(var)
            self._model.add_var(var)
        else:
            self._vars.add(var)

    def _remove_var(self, var):
        if self._vars.count(var) == 1:
            self._model.remove_var(var)
        self._vars.remove(var)

    def _register_constraint(self, con):
        for v in con.py_get_vars():
            self._register_var(v)
        self._cons.add(con)
        self._model.add_constraint(con)

    def _remove_constraint(self, con):
        self._model.remove_constraint(con)
        self._cons.remove(con)
        for v in con.py_get_vars():
            self._remove_var(v)

    def _register_objective(self, obj):
        if len(self._obj) != 0:
            raise ValueError('The model already contains an objective: {0}'.format(self._obj))
        for v in obj.py_get_vars():
            self._register_var(v)
        self._obj.append(obj)
        self._model.set_objective(obj)

    def _remove_objective(self):
        for v in self._obj.py_get_vars():
            self._remove_var(v)
        self._obj = list()

    def evaluate_residuals(self, x=None):
        if x is not None:
            self._model.load_var_values_from_x(x)
        r = self._model.evaluate(len(self._cons))
        return r

    def evaluate_jacobian(self, x=None, new_eval=True):
        if x is not None:
            self._model.load_var_values_from_x(x)
        if new_eval:
            self.evaluate_residuals()
        jac_values = self._model.jac.evaluate(len(self._model.jac.cons), False)
        n_vars = len(self._vars)
        n_cons = len(self._cons)
        if n_vars != n_cons:
            raise ValueError('The number of constraints and variables must be equal.')
        result = scipy.sparse.csr_matrix((jac_values, self._model.jac.get_col_ndx(), self._model.jac.get_row_nnz()),
                                         shape=(n_cons, n_vars))
        return result

    def get_x(self):
        return self._model.get_x(len(self._vars))

    def load_var_values_from_x(self, x):
        self._model.load_var_values_from_x(x)

    def solve(self):
        self._model.solve()

    def __str__(self):
        tmp = 'cons:\n'
        for con in self._cons:
            tmp += str(con.name)
            tmp += ':   '
            tmp += con._print()
            tmp += '\n'
        tmp += '\n'
        tmp += 'vars:\n'
        for var in self._vars:
            tmp += str(var.name)
            tmp += ':   '
            tmp += var._print()
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
    pass


class ConstraintDict(_NodeDict):
    """
    Dictionary of constraints; primarily handles registering the constraints with the model and naming
    """
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
        if hasattr(self, key):
            raise ValueError('ConstraintDict already has a Constraint named {0}. If you want to replace the Constraint, please remove the existing one first.'.format(key))
        val.name = self.name + '[' + str(key) + ']'
        if self._model is not None:
            self._model._register_constraint(val)
        self._data[key] = val
