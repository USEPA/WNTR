import sys
import scipy
from .evaluator import Evaluator
from .expr import Var, Param, native_numeric_types, Float, ConditionalExpression
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet
if sys.version_info.major == 2:
    from collections import MutableMapping
else:
    from collections.abc import MutableMapping


class Constraint(object):
    __slots__ = ('_expr', 'name', '_c_obj')

    def __init__(self, expr):
        """

        Parameters
        ----------
        expr: wntr.aml.expr.ExpressionBase
        """
        self._expr = expr
        self.name = None
        self._c_obj = None

    @property
    def expr(self):
        return self._expr

    @property
    def index(self):
        if self._c_obj is None:
            return None
        else:
            return self._c_obj.index

    def evaluate(self):
        return self.expr.evaluate()

    def reverse_ad(self):
        return self.expr.reverse_ad()


class Model(object):
    """
    A class for creating algebraic models.
    """
    def __init__(self):
        self._evaluator = Evaluator()
        self._refcounts = OrderedDict()
        self._con_ccon_map = OrderedDict()
        self._var_cvar_map = OrderedDict()
        self._param_cparam_map = OrderedDict()
        self._float_cfloat_map = OrderedDict()
        self._vars_referenced_by_con = OrderedDict()
        self._params_referenced_by_con = OrderedDict()
        self._floats_referenced_by_con = OrderedDict()

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
        if isinstance(val, (Var, Param, Constraint, _NodeDict)):
            if hasattr(self, name):
                raise ValueError('Model already has a {0} named {1}. If you want to replace the {0}, please remove the existing one first.'.format(type(val), name))

        if type(val) == Constraint:
            val.name = name
            self._register_constraint(val)
        elif type(val) == ConstraintDict:
            val.name = name
            val._model = self
            for k, v in val.items():
                self._register_constraint(v)
        elif type(val) in {Var, Param, VarDict, ParamDict}:
            val.name = name

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
        if type(val) == Constraint:
            self._remove_constraint(val)
            val.name = 'None'
        elif type(val) == ConstraintDict():
            val.name = 'None'
            val._model = None
            for k, v in val.items():
                self._remove_constraint(v)
        elif type(val) in {Var, Param, VarDict, ParamDict}:
            val.name = 'None'

        super(Model, self).__delattr__(name)

    def _increment_var(self, var):
        if var not in self._var_cvar_map:
            cvar = self._evaluator.add_var(var.value)
            var._c_obj = cvar
            self._var_cvar_map[var] = cvar
            self._refcounts[var] = 1
        else:
            self._refcounts[var] += 1
            cvar = self._var_cvar_map[var]
        return cvar

    def _increment_param(self, param):
        if param not in self._param_cparam_map:
            cparam = self._evaluator.add_param(param.value)
            param._c_obj = cparam
            self._param_cparam_map[param] = cparam
            self._refcounts[param] = 1
        else:
            self._refcounts[param] += 1
            cparam = self._param_cparam_map[param]
        return cparam

    def _increment_float(self, f):
        if f not in self._float_cfloat_map:
            cfloat = self._evaluator.add_float(f.value)
            f._c_obj = cfloat
            self._float_cfloat_map[f] = cfloat
            self._refcounts[f] = 1
        else:
            self._refcounts[f] += 1
            cfloat = self._var_cvar_map[f]
        return cfloat

    def _decrement_var(self, var):
        self._refcounts[var] -= 1
        if self._refcounts[var] == 0:
            cvar = self._var_cvar_map[var]
            var._c_obj = None
            del self._refcounts[var]
            del self._var_cvar_map[var]
            self._evaluator.remove_var(cvar)

    def _decrement_param(self, p):
        self._refcounts[p] -= 1
        if self._refcounts[p] == 0:
            cparam = self._param_cparam_map[p]
            p._c_obj = None
            del self._refcounts[p]
            del self._param_cparam_map[p]
            self._evaluator.remove_param(cparam)

    def _decrement_float(self, f):
        self._refcounts[f] -= 1
        if self._refcounts[f] == 0:
            cfloat = self._float_cfloat_map[f]
            f._c_obj = None
            del self._refcounts[f]
            del self._float_cfloat_map[f]
            self._evaluator.remove_float(cfloat)

    def _register_conditional_constraint(self, con):
        ccon = self._evaluator.add_if_else_constraint()
        con._c_obj = ccon
        self._con_ccon_map[con] = ccon
        leaf_ndx_map = OrderedDict()
        referenced_vars = OrderedSet()
        referenced_params = OrderedSet()
        referenced_floats = OrderedSet()
        ndx = 0
        derivs = list()
        for expr in con.expr._conditions:
            referenced_vars.update(expr.get_vars())
            referenced_params.update(expr.get_params())
            referenced_floats.update(expr.get_floats())
        for expr in con.expr._exprs:
            referenced_vars.update(expr.get_vars())
            referenced_params.update(expr.get_params())
            referenced_floats.update(expr.get_floats())
        for expr in con.expr._exprs:
            _deriv = expr.reverse_sd()
            derivs.append(_deriv)
            for v in referenced_vars:
                if v not in _deriv:
                    _deriv[v] = Float(0)
                elif type(_deriv[v]) in native_numeric_types:
                    _deriv[v] = Float(_deriv[v])
                referenced_floats.update(_deriv[v].get_floats())

        for v in referenced_vars:
            leaf_ndx_map[v] = ndx
            ndx += 1
            cvar = self._increment_var(v)
            ccon.add_leaf(cvar)
        for v in referenced_params:
            leaf_ndx_map[v] = ndx
            ndx += 1
            cvar = self._increment_param(v)
            ccon.add_leaf(cvar)
        for v in referenced_floats:
            leaf_ndx_map[v] = ndx
            ndx += 1
            cvar = self._increment_float(v)
            ccon.add_leaf(cvar)

        for i in range(len(con.expr._conditions)):
            condition_rpn = con.expr._conditions[i].get_rpn(leaf_ndx_map)
            for term in condition_rpn:
                ccon.add_condition_rpn_term(term)
            fn_rpn = con.expr._exprs[i].get_rpn(leaf_ndx_map)
            for term in fn_rpn:
                ccon.add_fn_rpn_term(term)
            for v in referenced_vars:
                cvar = v._c_obj
                jac = derivs[i][v]
                jac_rpn = jac.get_rpn(leaf_ndx_map)
                for term in jac_rpn:
                    ccon.add_jac_rpn_term(cvar, term)
            ccon.end_condition()

        self._vars_referenced_by_con[con] = referenced_vars
        self._params_referenced_by_con[con] = referenced_params
        self._floats_referenced_by_con[con] = referenced_floats

    def _register_constraint(self, con):
        if type(con.expr) == ConditionalExpression:
            self._register_conditional_constraint(con)
            return None
        ccon = self._evaluator.add_constraint()
        con._c_obj = ccon
        self._con_ccon_map[con] = ccon
        leaf_ndx_map = OrderedDict()
        referenced_vars = OrderedSet()
        referenced_params = OrderedSet()
        referenced_floats = OrderedSet()
        ndx = 0
        for v in con.expr.get_vars():
            leaf_ndx_map[v] = ndx
            ndx += 1
            cvar = self._increment_var(v)
            ccon.add_leaf(cvar)
            referenced_vars.add(v)
        for p in con.expr.get_params():
            leaf_ndx_map[p] = ndx
            ndx += 1
            cparam = self._increment_param(p)
            ccon.add_leaf(cparam)
            referenced_params.add(p)
        for f in con.expr.get_floats():
            leaf_ndx_map[f] = ndx
            ndx += 1
            cfloat = self._increment_float(f)
            ccon.add_leaf(cfloat)
            referenced_floats.add(f)
        fn_rpn = con.expr.get_rpn(leaf_ndx_map)
        for term in fn_rpn:
            ccon.add_fn_rpn_term(term)
        jac = con.expr.reverse_sd()
        for v in con.expr.get_vars():
            jac_v = jac[v]
            if type(jac_v) in native_numeric_types:
                jac_v = Float(jac_v)
            for f in jac_v.get_floats():
                if f not in leaf_ndx_map:
                    leaf_ndx_map[f] = ndx
                    ndx += 1
                    cfloat = self._increment_float(f)
                    ccon.add_leaf(cfloat)
                    referenced_floats.add(f)
            jac_rpn = jac_v.get_rpn(leaf_ndx_map)
            cvar = self._var_cvar_map[v]
            for term in jac_rpn:
                ccon.add_jac_rpn_term(cvar, term)
        self._vars_referenced_by_con[con] = referenced_vars
        self._params_referenced_by_con[con] = referenced_params
        self._floats_referenced_by_con[con] = referenced_floats

    def _remove_conditional_constraint(self, con):
        self._evaluator.remove_if_else_constraint(self._con_ccon_map[con])
        del self._con_ccon_map[con]
        for v in self._vars_referenced_by_con[con]:
            self._decrement_var(v)
        for p in self._params_referenced_by_con[con]:
            self._decrement_param(p)
        for f in self._floats_referenced_by_con[con]:
            self._decrement_float(f)
        del self._vars_referenced_by_con[con]
        del self._params_referenced_by_con[con]
        del self._floats_referenced_by_con[con]

    def _remove_constraint(self, con):
        if type(con.expr) == ConditionalExpression:
            self._remove_conditional_constraint(con)
            return None
        self._evaluator.remove_constraint(self._con_ccon_map[con])
        del self._con_ccon_map[con]
        for v in self._vars_referenced_by_con[con]:
            self._decrement_var(v)
        for p in self._params_referenced_by_con[con]:
            self._decrement_param(p)
        for f in self._floats_referenced_by_con[con]:
            self._decrement_float(f)
        del self._vars_referenced_by_con[con]
        del self._params_referenced_by_con[con]
        del self._floats_referenced_by_con[con]

    def evaluate_residuals(self, x=None, num_threads=4):
        if x is not None:
            self._evaluator.load_var_values_from_x(x)
        r = self._evaluator.evaluate(len(self._con_ccon_map))
        return r

    def evaluate_jacobian(self, x=None):
        n_vars = len(self._var_cvar_map)
        n_cons = len(self._con_ccon_map)
        if n_vars != n_cons:
            raise ValueError('The number of constraints and variables must be equal.')
        if x is not None:
            self._evaluator.load_var_values_from_x(x)
        jac_values, col_ndx, row_nnz = self._evaluator.evaluate_csr_jacobian(self._evaluator.nnz,
                                                                             self._evaluator.nnz,
                                                                             len(self._con_ccon_map) + 1)
        result = scipy.sparse.csr_matrix((jac_values, col_ndx, row_nnz), shape=(n_cons, n_vars))
        return result

    def get_x(self):
        return self._evaluator.get_x(len(self._var_cvar_map))

    def load_var_values_from_x(self, x):
        self._evaluator.load_var_values_from_x(x)

    def __str__(self):
        tmp = 'cons:\n'
        for con in self._con_ccon_map.keys():
            tmp += str(con.name)
            tmp += ':   '
            tmp += str(con.expr)
            tmp += '\n'
        tmp += '\n'
        tmp += 'vars:\n'
        for var in self._var_cvar_map:
            tmp += str(var.name)
            tmp += ':   '
            tmp += str(var)
            tmp += '\n'
        return tmp

    def set_structure(self):
        """
        This method essentially just orders all of the variables and constraints so that
        the constraint residuals and the jacobian can be evaluated efficiently. This method
        must be called before get_x, load_var_values_from_x, evaluate_residuals, or evaluate_jacobian
        can be called. If any changes are made to the model (e.g., variables/constraints are
        added/removed), then this method needs called again. Avoid calling this method too often
        if you are concerned about efficiency.
        """
        self._evaluator.set_structure()

    def cons(self):
        for i in self._con_ccon_map:
            yield i

    def vars(self):
        for i in self._var_cvar_map:
            yield i


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
        if key in self:
            raise ValueError('ConstraintDict already has a Constraint named {0}. If you want to replace the Constraint, please remove the existing one first.'.format(key))
        val.name = self.name + '[' + str(key) + ']'
        if self._model is not None:
            self._model._register_constraint(val)
        self._data[key] = val
