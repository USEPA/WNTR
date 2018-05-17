import sys
from collections import OrderedDict
from wntr.aml.aml.expression import Var, Param, create_var, create_param
from wntr.aml.aml.component import ConstraintBase, Constraint, ConditionalConstraint, Objective, create_constraint, create_conditional_constraint, create_objective
from wntr.aml.aml.ipopt_model import IpoptModel
from wntr.aml.aml.wntr_model import WNTRModel, CSRJacobian
if sys.version_info.major == 2:
    from collections import MutableSet, MutableMapping
else:
    from collections.abc import MutableSet, MutableMapping
import scipy


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
    def __init__(self, model_type='wntr'):
        self._vars = _OrderedIndexSet()
        self._cons = _OrderedIndexSet()
        if model_type.upper() == 'WNTR':
            self._model = WNTRModel()
        elif model_type.upper() == 'IPOPT':
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
        if isinstance(val, Param):
            if hasattr(self, name):
                raise ValueError('Model already has a parameter named {0}. If you want to replace the parameter, please remove the existing one first.'.format(name))
            val.name = name
        elif isinstance(val, Var):
            if hasattr(self, name):
                raise ValueError('Model already has a var named {0}. If you want to replace the var, please remove the existing one first.'.format(name))
            val.name = name
            self._register_var(val)
        elif isinstance(val, ConstraintBase):
            if hasattr(self, name):
                raise ValueError('Model already has a constraint named {0}. If you want to replace the constraint, please remove the existing one first.'.format(name))
            val.name = name
            self._register_constraint(val)
        elif isinstance(val, VarDict):
            if hasattr(self, name):
                raise ValueError('Model already has a VarDict named {0}. If you want to replace the VarDict, please remove the existing one first.'.format(name))
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_var(v)
        elif isinstance(val, ParamDict):
            if hasattr(self, name):
                raise ValueError('Model already has a ParamDict named {0}. If you want to replace the ParamDict, please remove the existing one first.'.format(name))
            val.name = name
        elif isinstance(val, ConstraintDict):
            if hasattr(self, name):
                raise ValueError('Model already has a ConstraintDict named {0}. If you want to replace the ConstraintDict, please remove the existing one first.'.format(name))
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_constraint(v)
        elif isinstance(val, Objective):
            self._model.set_objective(val)

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
        if isinstance(val, ConstraintBase):
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
        if hasattr(self, key):
            raise ValueError('VarDict already has a Var named {0}. If you want to replace the Var, please remove the existing one first.'.format(key))
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
        if hasattr(self, key):
            raise ValueError('ConstraintDict already has a Constraint named {0}. If you want to replace the Constraint, please remove the existing one first.'.format(key))
        val.name = self.name + '[' + str(key) + ']'
        if self._model is not None:
            self._model._register_constraint(val)
        self._data[key] = val
