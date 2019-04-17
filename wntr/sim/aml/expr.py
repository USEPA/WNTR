import abc
import itertools
import operator
import math
from wntr.utils.ordered_set import OrderedSet
import enum
from six import with_metaclass

if not hasattr(math, 'inf'):
    math.inf = float('inf')

native_numeric_types = {float, int}
native_integer_types = {int, bool}
native_boolean_types = {int, bool, str}


class OperationEnum(enum.IntEnum):
    add = -1
    sub = -2
    mul = -3
    div = -4
    pow = -5
    abs = -6
    sign = -7
    if_else = -8
    inequality = -9
    exp = -10
    log = -11
    negation = -12
    sin = -13
    cos = -14
    tan = -15
    asin = -16
    acos = -17
    atan = -18


class Node(with_metaclass(abc.ABCMeta, object)):

    __slots__ = ()

    @abc.abstractmethod
    def is_leaf(self):
        pass


class ExpressionBase(with_metaclass(abc.ABCMeta, Node)):
    """
    A base class for expressions (including variables and params).
    """
    __slots__ = ()

    def is_relational(self):
        return False

    @abc.abstractmethod
    def operators(self):
        pass

    @abc.abstractmethod
    def last_node(self):
        pass

    @abc.abstractmethod
    def evaluate(self):
        """
        Evaluate the expression numerically.

        Returns
        -------
        val: float
            The floating point value of the expression.
        """
        pass

    @abc.abstractmethod
    def _binary_operation_helper(self, other, cls):
        pass

    @abc.abstractmethod
    def _unary_operation_helper(self, cls):
        pass

    def __add__(self, other):
        if other == 0:
            return self
        return self._binary_operation_helper(other, AddOperator)

    def __sub__(self, other):
        if other == 0:
            return self
        return self._binary_operation_helper(other, SubtractOperator)

    def __mul__(self, other):
        if other == 0:
            return 0
        elif other == 1:
            return self
        return self._binary_operation_helper(other, MultiplyOperator)

    def __truediv__(self, other):
        if other == 0:
            raise ValueError('Divide by 0')
        elif other == 1:
            return self
        return self._binary_operation_helper(other, DivideOperator)

    def __div__(self, other):
        if other == 0:
            raise ValueError('Divide by 0')
        elif other == 1:
            return self
        return self._binary_operation_helper(other, DivideOperator)

    def __pow__(self, other):
        if other == 0:
            return 1
        elif other == 1:
            return self
        return self._binary_operation_helper(other, PowerOperator)

    def __radd__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return self
        return Float(other) + self

    def __rsub__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return -self
        return Float(other) - self

    def __rmul__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return 0
        elif other == 1:
            return self
        return Float(other) * self

    def __rtruediv__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return 0
        return Float(other) / self

    def __rdiv__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return 0
        return Float(other) / self

    def __rpow__(self, other):
        assert type(other) in native_numeric_types
        if other == 0:
            return 0
        elif other == 1:
            return 1
        return Float(other) ** self

    def __neg__(self):
        return self._unary_operation_helper(NegationOperator)

    @abc.abstractmethod
    def get_vars(self):
        pass

    @abc.abstractmethod
    def get_params(self):
        pass

    @abc.abstractmethod
    def get_floats(self):
        pass

    @abc.abstractmethod
    def get_leaves(self):
        pass

    @abc.abstractmethod
    def is_parameter_type(self):
        pass

    @abc.abstractmethod
    def is_variable_type(self):
        pass

    @abc.abstractmethod
    def is_float_type(self):
        pass

    @abc.abstractmethod
    def is_expression_type(self):
        pass

    @abc.abstractmethod
    def reverse_ad(self):
        pass

    @abc.abstractmethod
    def reverse_sd(self):
        pass

    @abc.abstractmethod
    def get_rpn(self, leaf_ndx_map):
        pass

    def __repr__(self):
        return str(self)


class Leaf(with_metaclass(abc.ABCMeta, ExpressionBase)):

    __slots__ = ('_value', '_c_obj')

    def is_leaf(self):
        return True

    def _binary_operation_helper(self, other, cls):
        if type(other) in native_numeric_types:
            other = Float(other)
        new_operator = cls(self, other.last_node())
        if other.is_leaf():
            expr = expression()
        else:
            expr = expression(other)
        expr.append_operator(new_operator)
        return expr

    def _unary_operation_helper(self, cls):
        new_operator = cls(self)
        expr = expression()
        expr.append_operator(new_operator)
        return expr

    def last_node(self):
        return self

    def operators(self):
        return list()

    @property
    def value(self):
        if self._c_obj is not None:
            return self._c_obj.value
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        if self._c_obj is not None:
            self._c_obj.value = val

    def evaluate(self):
        return self._value

    @abc.abstractmethod
    def _str(self):
        pass

    def __str__(self):
        return self._str()

    def reverse_ad(self):
        return {self: 1}

    def reverse_sd(self):
        return {self: 1}

    def get_rpn(self, leaf_ndx_map):
        return [leaf_ndx_map[self]]


class Float(Leaf):

    __slots__ = ()

    def __init__(self, val):
        self._value = val
        self._c_obj = None

    def is_parameter_type(self):
        return False

    def is_variable_type(self):
        return False

    def is_float_type(self):
        return True

    def is_expression_type(self):
        return False

    def _str(self):
        return str(self.value)

    def get_vars(self):
        return OrderedSet()

    def get_params(self):
        return OrderedSet()

    def get_floats(self):
        return OrderedSet([self])

    def get_leaves(self):
        return OrderedSet([self])

    def _binary_operation_helper(self, other, cls):
        if type(other) in native_numeric_types:
            return cls.operation(self.value, other)
        elif other.is_float_type():
            return cls.operation(self.value, other.value)
        new_operator = cls(self, other.last_node())
        if other.is_leaf():
            expr = expression()
        else:
            expr = expression(other)
        expr.append_operator(new_operator)
        return expr

    def _unary_operation_helper(self, cls):
        return cls.operation(self.value)


class Var(Leaf):
    """
    Variables

    Parameters
    ----------
    val: float
        value of the variable
    """

    __slots__ = ('_name',)

    def __init__(self, val=0):
        self._value = val
        self._name = None
        self._c_obj = None

    def is_parameter_type(self):
        return False

    def is_variable_type(self):
        return True

    def is_float_type(self):
        return False

    def is_expression_type(self):
        return False

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = val

    def _str(self):
        return str(self.name)

    def get_vars(self):
        return OrderedSet([self])

    def get_params(self):
        return OrderedSet()

    def get_floats(self):
        return OrderedSet()

    def get_leaves(self):
        return OrderedSet([self])

    @property
    def index(self):
        if self._c_obj is None:
            return None
        else:
            return self._c_obj.index


class Param(Leaf):

    __slots__ = ('_name',)

    def __init__(self, val=0):
        self._value = val
        self._name = None
        self._c_obj = None

    def is_parameter_type(self):
        return True

    def is_variable_type(self):
        return False

    def is_float_type(self):
        return False

    def is_expression_type(self):
        return False

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = val

    def _str(self):
        return str(self.name)

    def get_vars(self):
        return OrderedSet()

    def get_params(self):
        return OrderedSet([self])

    def get_floats(self):
        return OrderedSet()

    def get_leaves(self):
        return OrderedSet([self])


class expression(ExpressionBase):

    __slots__ = ('_operators', '_n_opers', '_vars', '_params', '_floats')

    def __init__(self, expr=None):
        """

        Parameters
        ----------
        expr: expression
        """
        if expr is not None:
            if expr._operators[-1] is not expr.last_node():
                self._operators = expr.list_of_operators()
            else:
                self._operators = expr._operators
        else:
            self._operators = []
        self._n_opers = len(self._operators)
        self._vars = None
        self._params = None
        self._floats = None

    def append_operator(self, oper):
        self._operators.append(oper)
        self._n_opers += 1

    def last_node(self):
        """
        Returns
        -------
        last_node: Operator
        """
        return self._operators[self._n_opers - 1]

    def list_of_operators(self):
        return self._operators[:self._n_opers]

    def is_leaf(self):
        return False

    def operators(self):
        return itertools.islice(self._operators, 0, self._n_opers)

    def _binary_operation_helper(self, other, cls):
        if type(other) in native_numeric_types:
            other = Float(other)
        new_operator = cls(self.last_node(), other.last_node())
        expr = expression(self)
        for oper in other.operators():
            expr.append_operator(oper)
        expr.append_operator(new_operator)
        return expr

    def _unary_operation_helper(self, cls):
        new_operator = cls(self.last_node())
        expr = expression(self)
        expr.append_operator(new_operator)
        return expr

    def evaluate(self):
        val_dict = dict()
        for oper in self.operators():
            oper.evaluate(val_dict)
        return val_dict[self.last_node()]

    def get_vars(self):
        if self._vars is None:
            self._collect_leaves()
        for i in self._vars:
            yield i

    def get_params(self):
        if self._params is None:
            self._collect_leaves()
        for i in self._params:
            yield i

    def get_floats(self):
        if self._floats is None:
            self._collect_leaves()
        for i in self._floats:
            yield i

    def _collect_leaves(self):
        self._vars = OrderedSet()
        self._params = OrderedSet()
        self._floats = OrderedSet()
        for oper in self.operators():
            for operand in oper.operands():
                if operand.is_leaf():
                    if operand.is_variable_type():
                        self._vars.add(operand)
                    elif operand.is_parameter_type():
                        self._params.add(operand)
                    elif operand.is_float_type():
                        self._floats.add(operand)
                    elif operand.is_expression_type():
                        self._vars.update(operand.get_vars())
                        self._params.update(operand.get_params())
                        self._floats.update(operand.get_floats())
                    else:
                        raise ValueError('operand type not recognized: ' + str(operand))

    def get_leaves(self):
        if self._vars is None:
            self._collect_leaves()
        for i in self._vars:
            yield i
        for i in self._params:
            yield i
        for i in self._floats:
            yield i

    def _str(self):
        return str(self)

    def __str__(self):
        val_dict = dict()
        for oper in self.operators():
            oper._str(val_dict)
        return val_dict[self.last_node()]

    def is_variable_type(self):
        return False

    def is_parameter_type(self):
        return False

    def is_float_type(self):
        return False

    def is_expression_type(self):
        return True

    def reverse_ad(self):
        val_dict = dict()
        der_dict = dict()
        for oper in self.operators():
            oper.diff_up(val_dict, der_dict)
        der_dict[self.last_node()] = 1
        for oper in reversed(self.list_of_operators()):
            oper.diff_down(val_dict, der_dict)
        return der_dict

    def reverse_sd(self):
        val_dict = dict()
        der_dict = dict()
        for oper in self.operators():
            oper.diff_up_symbolic(val_dict, der_dict)
        der_dict[self.last_node()] = 1
        for oper in reversed(self.list_of_operators()):
            oper.diff_down(val_dict, der_dict)
        return der_dict

    def is_relational(self):
        if type(self.last_node()) in {InequalityOperator}:
            return True
        return False

    def get_rpn(self, leaf_ndx_map):
        rpn_map = dict()
        for oper in self.operators():
            oper.get_rpn(rpn_map, leaf_ndx_map)
        return rpn_map[self.last_node()]


class Operator(with_metaclass(abc.ABCMeta, Node)):

    __slots__ = ()

    def is_leaf(self):
        return False

    @abc.abstractmethod
    def evaluate(self, val_dict):
        pass

    @abc.abstractmethod
    def operands(self):
        pass

    @abc.abstractmethod
    def diff_up(self, val_dict, der_dict):
        pass

    @abc.abstractmethod
    def diff_down(self, val_dict, der_dict):
        pass

    @abc.abstractmethod
    def diff_up_symbolic(self, val_dict, der_dict):
        pass

    @abc.abstractmethod
    def get_rpn(self, rpn_map, leaf_ndx_map):
        pass


class BinaryOperator(Operator):

    __slots__ = ('_operand1', '_operand2')

    operation = None
    str_repn = None
    operation_enum = None

    def __init__(self, operand1, operand2):
        self._operand1 = operand1
        self._operand2 = operand2

    def evaluate(self, val_dict):
        if self._operand1.is_leaf():
            val1 = self._operand1.value
        else:
            val1 = val_dict[self._operand1]
        if self._operand2.is_leaf():
            val2 = self._operand2.value
        else:
            val2 = val_dict[self._operand2]
        val_dict[self] = self.operation(val1, val2)

    def _str(self, val_dict):
        if self._operand1.is_leaf():
            val1 = self._operand1._str()
        else:
            val1 = val_dict[self._operand1]
        if self._operand2.is_leaf():
            val2 = self._operand2._str()
        else:
            val2 = val_dict[self._operand2]
        val_dict[self] = '(' + val1 + self.str_repn + val2 + ')'

    def operands(self):
        yield self._operand1
        yield self._operand2

    def diff_up(self, val_dict, der_dict):
        if self._operand1.is_leaf():
            val1 = self._operand1.value
            val_dict[self._operand1] = val1
            if self._operand1 not in der_dict:
                der_dict[self._operand1] = 0
        else:
            val1 = val_dict[self._operand1]
            der_dict[self._operand1] = 0
        if self._operand2.is_leaf():
            val2 = self._operand2.value
            val_dict[self._operand2] = val2
            if self._operand2 not in der_dict:
                der_dict[self._operand2] = 0
        else:
            val2 = val_dict[self._operand2]
            der_dict[self._operand2] = 0
        val_dict[self] = self.operation(val1, val2)

    def diff_up_symbolic(self, val_dict, der_dict):
        if self._operand1.is_leaf():
            val1 = self._operand1
            val_dict[self._operand1] = val1
            if self._operand1 not in der_dict:
                der_dict[self._operand1] = 0
        else:
            val1 = val_dict[self._operand1]
            der_dict[self._operand1] = 0
        if self._operand2.is_leaf():
            val2 = self._operand2
            val_dict[self._operand2] = val2
            if self._operand2 not in der_dict:
                der_dict[self._operand2] = 0
        else:
            val2 = val_dict[self._operand2]
            der_dict[self._operand2] = 0
        val_dict[self] = self.operation(val1, val2)

    def get_rpn(self, rpn_map, leaf_ndx_map):
        if self._operand2.is_leaf():
            if self._operand1.is_leaf():
                rpn_map[self] = [leaf_ndx_map[self._operand1], leaf_ndx_map[self._operand2], self.operation_enum]
            else:
                rpn_map[self] = _rpn = rpn_map[self._operand1]
                _rpn.append(leaf_ndx_map[self._operand2])
                _rpn.append(self.operation_enum)
        elif self._operand1.is_leaf():
            rpn_map[self] = _rpn = rpn_map[self._operand2]
            _rpn.insert(0, leaf_ndx_map[self._operand1])
            _rpn.append(self.operation_enum)
        else:
            rpn_map[self] = _rpn = rpn_map[self._operand1]
            _rpn.extend(rpn_map[self._operand2])
            _rpn.append(self.operation_enum)


class AddOperator(BinaryOperator):

    __slots__ = ()

    operation = operator.add
    str_repn = '+'
    operation_enum = OperationEnum.add.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand1] += der
        der_dict[self._operand2] += der


class SubtractOperator(BinaryOperator):
    __slots__ = ()

    operation = operator.sub
    str_repn = '-'
    operation_enum = OperationEnum.sub.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand1] += der
        der_dict[self._operand2] -= der


class MultiplyOperator(BinaryOperator):
    __slots__ = ()

    operation = operator.mul
    str_repn = '*'
    operation_enum = OperationEnum.mul.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand1] += der * val_dict[self._operand2]
        der_dict[self._operand2] += der * val_dict[self._operand1]


class DivideOperator(BinaryOperator):
    __slots__ = ()

    operation = operator.truediv
    str_repn = '/'
    operation_enum = OperationEnum.div.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand1] += der / val_dict[self._operand2]
        der_dict[self._operand2] -= der * val_dict[self._operand1] / val_dict[self._operand2]**2


class PowerOperator(BinaryOperator):
    __slots__ = ()

    operation = operator.pow
    str_repn = '**'
    operation_enum = OperationEnum.pow.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        val1 = val_dict[self._operand1]
        val2 = val_dict[self._operand2]
        der_dict[self._operand1] += der * val2 * val1**(val2 - 1)
        if not self._operand2.is_leaf() or self._operand2.is_variable_type():
            der_dict[self._operand2] += der * val1**val2 * log(val1)


class UnaryOperator(Operator):
    __slots__ = ('_operand',)

    str_repn = None
    operation_enum = None

    def __init__(self, operand):
        """
        Parameters
        ----------
        operand: Node
        """
        self._operand = operand

    def evaluate(self, val_dict):
        if self._operand.is_leaf():
            val = self._operand.value
        else:
            val = val_dict[self._operand]
        val_dict[self] = self.operation(val)

    def _str(self, val_dict):
        if self._operand.is_leaf():
            val = self._operand._str()
        else:
            val = val_dict[self._operand]
        val_dict[self] = '(' + self.str_repn + '(' + val + ')' + ')'

    def operands(self):
        yield self._operand

    def diff_up(self, val_dict, der_dict):
        if self._operand.is_leaf():
            val = self._operand.value
            val_dict[self._operand] = val
            if self._operand not in der_dict:
                der_dict[self._operand] = 0
        else:
            val = val_dict[self._operand]
            der_dict[self._operand] = 0
        val_dict[self] = self.operation(val)

    def diff_up_symbolic(self, val_dict, der_dict):
        if self._operand.is_leaf():
            val = self._operand
            val_dict[self._operand] = val
            if self._operand not in der_dict:
                der_dict[self._operand] = 0
        else:
            val = val_dict[self._operand]
            der_dict[self._operand] = 0
        val_dict[self] = self.operation(val)

    def get_rpn(self, rpn_map, leaf_ndx_map):
        if self._operand.is_leaf():
            rpn_map[self] = [leaf_ndx_map[self._operand], self.operation_enum]
        else:
            rpn_map[self] = _rpn = rpn_map[self._operand]
            _rpn.append(self.operation_enum)

    @staticmethod
    def operation(val):
        raise NotImplementedError('Subclasses should implement this.')


class NegationOperator(UnaryOperator):
    __slots__ = ()

    str_repn = '-'
    operation_enum = OperationEnum.negation.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] -= der

    @staticmethod
    def operation(val):
        return -val


def exp(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.exp(val)
    return val._unary_operation_helper(ExpOperator)


def log(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.log(val)
    return val._unary_operation_helper(LogOperator)


def sin(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.sin(val)
    return val._unary_operation_helper(SinOperator)


def cos(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.cos(val)
    return val._unary_operation_helper(CosOperator)


def tan(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.tan(val)
    return val._unary_operation_helper(TanOperator)


def asin(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.asin(val)
    return val._unary_operation_helper(AsinOperator)


def acos(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.acos(val)
    return val._unary_operation_helper(AcosOperator)


def atan(val):
    """

    Parameters
    ----------
    val: ExpressionBase

    Returns
    -------
    expr: expression
    """
    if type(val) in native_numeric_types:
        return math.atan(val)
    return val._unary_operation_helper(AtanOperator)


def if_else(if_statement, then_statement, else_statement):
    """

    Parameters
    ----------
    if_statement: ExpressionBase
    then_statement: ExpressionBase
    else_statement: ExpressionBase

    Returns
    -------
    expr: ExpressionBase
    """
    if type(if_statement) in native_numeric_types or type(if_statement) in native_boolean_types:
        if if_statement:
            return then_statement
        else:
            return else_statement
    if type(then_statement) in native_numeric_types:
        then_statement = Float(then_statement)
    if type(else_statement) in native_numeric_types:
        else_statement = Float(else_statement)
    assert if_statement.is_relational()
    expr = expression(if_statement)
    new_operator = IfElseOperator(if_statement.last_node(), then_statement.last_node(), else_statement.last_node())
    for oper in then_statement.operators():
        expr.append_operator(oper)
    for oper in else_statement.operators():
        expr.append_operator(oper)
    expr.append_operator(new_operator)
    return expr


def inequality(body, lb=None, ub=None):
    """

    Parameters
    ----------
    body: ExpressionBase or float
    lb: float
    ub: float

    Returns
    -------
    expr: ExpressionBase
    """
    if lb is not None and ub is not None:
        if type(lb) not in native_numeric_types or type(ub) not in native_numeric_types:
            raise ValueError('inequality can only accept both lb and ub arguments if both are floats or ints.')

    if lb is None:
        lb = -math.inf
    if ub is None:
        ub = math.inf

    if type(lb) in native_numeric_types:
        lb = Float(lb)
    else:
        body -= lb
        lb = Float(0)

    if type(ub) in native_numeric_types:
        ub = Float(ub)
    else:
        body -= ub
        ub = Float(0)

    if type(body) in native_numeric_types:
        return lb.value <= body <= ub.value

    if body.is_leaf():
        expr = expression()
    else:
        expr = expression(body)
    new_operator = InequalityOperator(body.last_node(), lb=lb, ub=ub)
    expr.append_operator(new_operator)
    return expr


def sign(val):
    if type(val) in native_numeric_types:
        if val >= 0:
            return 1
        else:
            return -1
    return val._unary_operation_helper(SignOperator)


def abs(val):
    if type(val) in native_numeric_types:
        return math.fabs(val)
    return val._unary_operation_helper(AbsOperator)


class IfElseOperator(Operator):
    __slots__ = ('_if_arg', '_then_arg', '_else_arg')

    def __init__(self, if_arg, then_arg, else_arg):
        self._if_arg = if_arg
        self._then_arg = then_arg
        self._else_arg = else_arg

    def evaluate(self, val_dict):
        if_val = val_dict[self._if_arg]
        if if_val:
            if self._then_arg.is_leaf():
                res = self._then_arg.value
            else:
                res = val_dict[self._then_arg]
        else:
            if self._else_arg.is_leaf():
                res = self._else_arg.value
            else:
                res = val_dict[self._else_arg]
        val_dict[self] = res

    def operands(self):
        yield self._if_arg
        yield self._then_arg
        yield self._else_arg

    def _str(self, val_dict):
        if_val = val_dict[self._if_arg]
        if self._then_arg.is_leaf():
            then_str = self._then_arg._str()
        else:
            then_str = val_dict[self._then_arg]
        if self._else_arg.is_leaf():
            else_str = self._else_arg._str()
        else:
            else_str = val_dict[self._else_arg]
        s = '\n (\n'
        s += '  if ' + if_val + ':\n'
        s += '      ' + then_str.replace('\n', '\n    ') + '\n'
        s += '  else:\n'
        s += '      ' + else_str.replace('\n', '\n    ') + '\n'
        s += '  )\n'
        val_dict[self] = s

    def diff_up(self, val_dict, der_dict):
        if_val = val_dict[self._if_arg]
        der_dict[self._if_arg] = 0
        if if_val:
            if self._then_arg.is_leaf():
                val = self._then_arg.value
                val_dict[self._then_arg] = val
                if self._then_arg not in der_dict:
                    der_dict[self._then_arg] = 0
            else:
                val = val_dict[self._then_arg]
                der_dict[self._then_arg] = 0
            if self._else_arg.is_leaf():
                _val = self._else_arg.value
                val_dict[self._else_arg] = _val
                if self._else_arg not in der_dict:
                    der_dict[self._else_arg] = 0
            else:
                der_dict[self._else_arg] = 0
        else:
            if self._else_arg.is_leaf():
                val = self._else_arg.value
                val_dict[self._else_arg] = val
                if self._else_arg not in der_dict:
                    der_dict[self._else_arg] = 0
            else:
                val = val_dict[self._else_arg]
                der_dict[self._else_arg] = 0
            if self._then_arg.is_leaf():
                _val = self._then_arg.value
                val_dict[self._then_arg] = _val
                if self._then_arg not in der_dict:
                    der_dict[self._then_arg] = 0
            else:
                der_dict[self._then_arg] = 0
        val_dict[self] = val

    def diff_up_symbolic(self, val_dict, der_dict):
        der_dict[self._if_arg] = 0
        if_val = val_dict[self._if_arg]
        if self._then_arg.is_leaf():
            then_val = self._then_arg
            val_dict[self._then_arg] = then_val
            if self._then_arg not in der_dict:
                der_dict[self._then_arg] = 0
        else:
            then_val = val_dict[self._then_arg]
            der_dict[self._then_arg] = 0
        if self._else_arg.is_leaf():
            else_val = self._else_arg
            val_dict[self._else_arg] = else_val
            if self._else_arg not in der_dict:
                der_dict[self._else_arg] = 0
        else:
            else_val = val_dict[self._else_arg]
            der_dict[self._else_arg] = 0
        val_dict[self] = if_else(if_val, then_val, else_val)

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._then_arg] += if_else(val_dict[self._if_arg], der, 0)
        der_dict[self._else_arg] += if_else(val_dict[self._if_arg], 0, der)

    def get_rpn(self, rpn_map, leaf_ndx_map):
        if self._if_arg.is_leaf():
            rpn_map[self] = _rpn = [leaf_ndx_map[self._if_arg]]
        else:
            rpn_map[self] = _rpn = rpn_map[self._if_arg]
        if self._then_arg.is_leaf():
            _rpn.append(leaf_ndx_map[self._then_arg])
        else:
            _rpn.extend(rpn_map[self._then_arg])
        if self._else_arg.is_leaf():
            _rpn.append(leaf_ndx_map[self._else_arg])
        else:
            _rpn.extend(rpn_map[self._else_arg])
        _rpn.append(OperationEnum.if_else.value)


class InequalityOperator(Operator):
    __slots__ = ('_lb', '_ub', '_body')

    def __init__(self, body, lb, ub):
        self._body = body
        self._lb = lb
        self._ub = ub

    def evaluate(self, val_dict):
        if self._body.is_leaf():
            body_val = self._body.value
        else:
            body_val = val_dict[self._body]
        val_dict[self] = (self._lb.value <= body_val <= self._ub.value)

    def operands(self):
        yield self._body
        yield self._lb
        yield self._ub

    def _str(self, val_dict):
        if self._body.is_leaf():
            body_val = self._body._str()
        else:
            body_val = val_dict[self._body]
        val_dict[self] = '(' + self._lb._str() + ' <= ' + body_val + ' <= ' + self._ub._str() + ')'

    def diff_up(self, val_dict, der_dict):
        if self._body.is_leaf():
            body_val = self._body.value
            val_dict[self._body] = body_val
            if self._body not in der_dict:
                der_dict[self._body] = 0
        else:
            body_val = val_dict[self._body]
            der_dict[self._body] = 0
        val_dict[self] = (self._lb.value <= body_val <= self._ub.value)

    def diff_up_symbolic(self, val_dict, der_dict):
        if self._body.is_leaf():
            body_val = self._body
            val_dict[self._body] = body_val
            if self._body not in der_dict:
                der_dict[self._body] = 0
        else:
            body_val = val_dict[self._body]
            der_dict[self._body] = 0
        val_dict[self] = inequality(body_val, self._lb.value, self._ub.value)

    def diff_down(self, val_dict, der_dict):
        pass

    def get_rpn(self, rpn_map, leaf_ndx_map):
        if self._body.is_leaf():
            rpn_map[self] = _rpn = [leaf_ndx_map[self._body]]
        else:
            rpn_map[self] = _rpn = rpn_map[self._body]
        _rpn.append(leaf_ndx_map[self._lb])
        _rpn.append(leaf_ndx_map[self._ub])
        _rpn.append(OperationEnum.inequality.value)


class SignOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'sign'
    operation_enum = OperationEnum.sign.value

    def diff_down(self, val_dict, der_dict):
        pass

    @staticmethod
    def operation(val):
        return sign(val)


class AbsOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'abs'
    operation_enum = OperationEnum.abs.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der * if_else(if_statement=inequality(body=val_dict[self._operand], lb=0),
                                                 then_statement=Float(1), else_statement=Float(-1))

    @staticmethod
    def operation(val):
        return abs(val)


class ExpOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'exp'
    operation_enum = OperationEnum.exp.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der * exp(val_dict[self._operand])

    @staticmethod
    def operation(val):
        return exp(val)


class LogOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'log'
    operation_enum = OperationEnum.log.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der / val_dict[self._operand]

    @staticmethod
    def operation(val):
        return log(val)


class SinOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'sin'
    operation_enum = OperationEnum.sin.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der * cos(val_dict[self._operand])

    @staticmethod
    def operation(val):
        return sin(val)


class CosOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'cos'
    operation_enum = OperationEnum.cos.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] -= der * sin(val_dict[self._operand])

    @staticmethod
    def operation(val):
        return cos(val)


class TanOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'tan'
    operation_enum = OperationEnum.tan.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der / (cos(val_dict[self._operand])**2)

    @staticmethod
    def operation(val):
        return tan(val)


class AsinOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'asin'
    operation_enum = OperationEnum.asin.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der / (1 - val_dict[self._operand]**2)**0.5

    @staticmethod
    def operation(val):
        return asin(val)


class AcosOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'acos'
    operation_enum = OperationEnum.acos.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] -= der / (1 - val_dict[self._operand]**2)**0.5

    @staticmethod
    def operation(val):
        return acos(val)


class AtanOperator(UnaryOperator):
    __slots__ = ()

    str_repn = 'atan'
    operation_enum = OperationEnum.atan.value

    def diff_down(self, val_dict, der_dict):
        der = der_dict[self]
        der_dict[self._operand] += der / (1 + val_dict[self._operand]**2)

    @staticmethod
    def operation(val):
        return atan(val)


def value(obj):
    if type(obj) in native_numeric_types:
        return obj
    return obj.evaluate()


def is_variable_type(obj):
    """
    Returns True if the object is a variable.

    Parameters
    ----------
    obj: ExpressionBase
        Also accepts floats and ints

    Returns
    -------
    bool
    """
    if type(obj) in native_numeric_types:
        return False
    return obj.is_variable_type()


class ConditionalExpression(object):
    def __init__(self):
        self._conditions = list()
        self._exprs = list()

    def add_condition(self, condition, expr):
        assert condition.is_relational()
        self._conditions.append(condition)
        self._exprs.append(expr)

    def add_final_expr(self, expr):
        self._conditions.append(Float(1))
        self._exprs.append(expr)

    def evaluate(self):
        for i, cond in enumerate(self._conditions):
            if cond.evaluate():
                return self._exprs[i].evaluate()

    def reverse_ad(self):
        for i, cond in enumerate(self._conditions):
            if cond.evaluate():
                return self._exprs[i].reverse_ad()

    def __str__(self):
        i = 0
        s = '\n'
        for _cond, _expr in zip(self._conditions, self._exprs):
            if i == 0:
                s += 'if '
            else:
                s += 'elif '
            s += str(_cond)
            s += ':\n    '
            s += str(_expr)
            s += '\n'
            i += 1
        return s

    def __repr__(self):
        return self.__str__()
