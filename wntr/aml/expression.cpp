#include "expression.hpp"


std::shared_ptr<Var> create_var(double value, double lb, double ub)
{
  std::shared_ptr<Var> v = std::make_shared<Var>();
  v->value = value;
  v->lb = lb;
  v->ub = ub;
  return v;
}


std::shared_ptr<Param> create_param(double value)
{
  std::shared_ptr<Param> p = std::make_shared<Param>();
  p->value = value;
  return p;
}


std::shared_ptr<Float> create_float(double value)
{
  std::shared_ptr<Float> f = std::make_shared<Float>();
  f->value = value;
  return f;
}


std::shared_ptr<Expression> ExpressionBase::shallow_copy()
{
  throw std::runtime_error("Cannot create a shallow copy");
}


std::shared_ptr<Expression> Expression::shallow_copy()
{
  std::shared_ptr<Expression> new_expr = std::make_shared<Expression>();
  for (int i=0; i < num_operators; ++i)
    {
      new_expr->add_operator((*operators)[i]);
    }
  return new_expr;
}


std::shared_ptr<Expression> _expr_copy(ExpressionBase &n)
{
  std::shared_ptr<Expression> expr;
  if (n.get_num_operators() != (int) (n.get_operators()->size()))
    {
      expr = n.shallow_copy();
    }
  else
    {
      expr = std::make_shared<Expression>();
      expr->operators = n.get_operators();
      expr->num_operators = n.get_num_operators();
    }
  return expr;
}


template <class T>
std::shared_ptr<ExpressionBase> expr_expr_binary_helper(ExpressionBase &n1, ExpressionBase &n2)
{
  std::shared_ptr<Expression> expr = _expr_copy(n1);
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > _opers = n2.get_operators();
  int _num_opers = n2.get_num_operators();
  for (int i=0; i<_num_opers; ++i)
    {
      expr->add_operator((*_opers)[i]);
    }
  std::shared_ptr<T> op = std::make_shared<T>(n1.get_last_node(), n2.get_last_node());
  expr->add_operator(op);
  return expr;
}


template <class T>
std::shared_ptr<ExpressionBase> expr_leaf_binary_helper(ExpressionBase &n1, ExpressionBase &n2)
{
  std::shared_ptr<Expression> expr = _expr_copy(n1);
  std::shared_ptr<T> op = std::make_shared<T>(n1.get_last_node(), n2.shared_from_this());
  expr->add_operator(op);
  return expr;
}


template <class T>
std::shared_ptr<ExpressionBase> leaf_expr_binary_helper(ExpressionBase &n1, ExpressionBase &n2)
{
  std::shared_ptr<Expression> expr = _expr_copy(n2);
  std::shared_ptr<T> op = std::make_shared<T>(n1.shared_from_this(), n2.get_last_node());
  expr->add_operator(op);
  return expr;
}


template <class T>
std::shared_ptr<ExpressionBase> leaf_leaf_binary_helper(ExpressionBase &n1, ExpressionBase &n2)
{
  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
  std::shared_ptr<T> op = std::make_shared<T>(n1.shared_from_this(), n2.shared_from_this());
  expr->add_operator(op);
  return expr;
}


std::shared_ptr<ExpressionBase> Leaf::operator+(ExpressionBase& n)
{
  if (n.is_float() && n.evaluate() == 0.0)
    {
      return shared_from_this();
    }
  else if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<AddOperator>(*this, n);
    }
  else
    {
      return leaf_expr_binary_helper<AddOperator>(*this, n);
    }
}


std::shared_ptr<ExpressionBase> Float::operator+(ExpressionBase& n)
{
  if (n.is_float())
    {
      return create_float(value + n.evaluate());
    }
  else if (n.is_leaf())
    {
      if (value == 0.0)
	{
	  return n.shared_from_this();
	}
      else
	{
	  return leaf_leaf_binary_helper<AddOperator>(*this, n);
	}
    }
  else
    {
      if (value == 0.0)
	{
	  return _expr_copy(n);
	}
      else
	{
	  return leaf_expr_binary_helper<AddOperator>(*this, n);
	}
    }
}


std::shared_ptr<ExpressionBase> Expression::operator+(ExpressionBase& n)
{
  if (n.is_float() && n.evaluate() == 0.0)
    {
      return _expr_copy(*this);
    }
  else if (n.is_leaf())
    {
      return expr_leaf_binary_helper<AddOperator>(*this, n);
    }
  else
    {
      return expr_expr_binary_helper<AddOperator>(*this, n);
    }
}


std::shared_ptr<ExpressionBase> Leaf::operator-(ExpressionBase& n)
{
  if (n.is_float() && n.evaluate() == 0.0)
    {
      return shared_from_this();
    }
  else if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<SubtractOperator>(*this, n);
    }
  else
    {
      return leaf_expr_binary_helper<SubtractOperator>(*this, n);
    }
}


std::shared_ptr<ExpressionBase> Float::operator-(ExpressionBase& n)
{
  if (n.is_float())
    {
      return create_float(value - n.evaluate());
    }
  else if (n.is_leaf())
    {
      if (value == 0.0)
	{
	  return -n;
	}
      else
	{
	  return leaf_leaf_binary_helper<SubtractOperator>(*this, n);
	}
    }
  else
    {
      if (value == 0.0)
	{
	  return _expr_copy(*(-n));
	}
      else
	{
	  return leaf_expr_binary_helper<SubtractOperator>(*this, n);
	}
    }
}


std::shared_ptr<ExpressionBase> Expression::operator-(ExpressionBase& n)
{
  if (n.is_float() && n.evaluate() == 0.0)
    {
      return _expr_copy(*this);
    }
  else if (n.is_leaf())
    {
      return expr_leaf_binary_helper<SubtractOperator>(*this, n);
    }
  else
    {
      return expr_expr_binary_helper<SubtractOperator>(*this, n);
    }
}


std::shared_ptr<ExpressionBase> Leaf::operator*(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  return create_float(0.0);
	}
      else if (n.evaluate() == 1.0)
	{
	  return shared_from_this();
	}
    }
  if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<MultiplyOperator>(*this, n);
    }
  return leaf_expr_binary_helper<MultiplyOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Float::operator*(ExpressionBase& n)
{
  if (value == 0.0)
    {
      return shared_from_this();
    }
  if (n.is_float())
    {
      return create_float(value * n.evaluate());
    }
  if (n.is_leaf())
    {
      if (value == 1.0)
	{
	  return n.shared_from_this();
	}
      return leaf_leaf_binary_helper<MultiplyOperator>(*this, n);
    }
  if (value == 1.0)
    {
      return _expr_copy(n);
    }
  return leaf_expr_binary_helper<MultiplyOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Expression::operator*(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  return n.shared_from_this();
	}
      if (n.evaluate() == 1.0)
	{
	  return _expr_copy(*this);
	}
    }
  if (n.is_leaf())
    {
      return expr_leaf_binary_helper<MultiplyOperator>(*this, n);
    }
  return expr_expr_binary_helper<AddOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Leaf::operator/(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  throw std::runtime_error("Divide by zero.");
	}
      else if (n.evaluate() == 1.0)
	{
	  return shared_from_this();
	}
    }
  if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<DivideOperator>(*this, n);
    }
  return leaf_expr_binary_helper<DivideOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Float::operator/(ExpressionBase& n)
{
  if (value == 0.0)
    {
      if (n.is_float() && n.evaluate() == 0.0)
	{
	  throw std::runtime_error("Divide by zero.");	  
	}
      return shared_from_this();
    }
  if (n.is_float())
    {
      return create_float(value / n.evaluate());
    }
  if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<DivideOperator>(*this, n);
    }
  return leaf_expr_binary_helper<DivideOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Expression::operator/(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  throw std::runtime_error("Divide by zero.");	  
	}
      if (n.evaluate() == 1.0)
	{
	  return _expr_copy(*this);
	}
    }
  if (n.is_leaf())
    {
      return expr_leaf_binary_helper<DivideOperator>(*this, n);
    }
  return expr_expr_binary_helper<DivideOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator-()
{
  std::shared_ptr<Float> f = create_float(0.0);
  return (*f) - (*this);
}


std::shared_ptr<ExpressionBase> Leaf::__pow__(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  return create_float(1.0);
	}
      if (n.evaluate() == 1.0)
	{
	  return shared_from_this();
	}
    }
  if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<PowerOperator>(*this, n);
    }
  return leaf_expr_binary_helper<PowerOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Float::__pow__(ExpressionBase& n)
{
  if (value == 0.0)
    {
      if (n.is_float() && n.evaluate() == 0.0)
	{
	  throw std::runtime_error("Cannot compute zero to the power of zero.");
	}
      return shared_from_this();
    }
  if (value == 1.0)
    {
      return shared_from_this();
    }
  if (n.is_float())
    {
      return create_float(::pow(value, n.evaluate()));
    }
  if (n.is_leaf())
    {
      return leaf_leaf_binary_helper<PowerOperator>(*this, n);
    }
  return leaf_expr_binary_helper<PowerOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> Expression::__pow__(ExpressionBase& n)
{
  if (n.is_float())
    {
      if (n.evaluate() == 0.0)
	{
	  return create_float(1.0);
	}
      if (n.evaluate() == 1.0)
	{
	  return _expr_copy(*this);
	}
    }
  if (n.is_leaf())
    {
      return expr_leaf_binary_helper<PowerOperator>(*this, n);
    }
  return expr_expr_binary_helper<PowerOperator>(*this, n);
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator+(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*this) + (*f);
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator-(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*this) - (*f);
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator*(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*this) * (*f);
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator/(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*this) / (*f);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__pow__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return __pow__(*f);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__radd__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*f) + (*this);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__rsub__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*f) - (*this);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__rmul__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*f) * (*this);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__rdiv__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*f) / (*this);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__rtruediv__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return (*f) / (*this);
}


std::shared_ptr<ExpressionBase> ExpressionBase::__rpow__(double n)
{
  std::shared_ptr<Float> f = create_float(n);
  return f->__pow__(*this);
}


std::shared_ptr<std::vector<std::shared_ptr<Operator> > > ExpressionBase::get_operators()
{
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > ops = std::make_shared<std::vector<std::shared_ptr<Operator> > >();
  return ops;
}


int ExpressionBase::get_num_operators()
{
  return 0;
}


bool ExpressionBase::is_leaf()
{
  return false;
}


bool ExpressionBase::is_var()
{
  return false;
}


bool ExpressionBase::is_param()
{
  return false;
}


bool ExpressionBase::is_float()
{
  return false;
}


bool ExpressionBase::is_expr()
{
  return false;
}


std::shared_ptr<Node> ExpressionBase::get_last_node()
{
  return shared_from_this();
}


bool Leaf::is_leaf()
{
  return true;
}


double Leaf::evaluate()
{
  return value;
}


bool Var::is_var()
{
  return true;
}


std::string Var::__str__()
{
  return name;
}


bool Float::is_float()
{
  return true;
}


std::string Float::__str__()
{
  std::ostringstream s;
  s << value;
  return s.str();
}


bool Param::is_param()
{
  return true;
}


std::string Param::__str__()
{
  if (name == "")
    {
      std::ostringstream s;
      s << value;
      return s.str();
    }
  else
    {
      return name;
    }
}


std::shared_ptr<std::vector<std::shared_ptr<Operator> > > Expression::get_operators()
{
  return operators;
}


int Expression::get_num_operators()
{
  return num_operators;
}


bool Expression::is_expr()
{
  return true;
}


std::shared_ptr<Node> Expression::get_last_node()
{
  return (*operators)[num_operators-1];
}


std::string Expression::__str__()
{
  return "not implemented yet";
}


void Expression::add_operator(std::shared_ptr<Operator> oper)
{
  operators->push_back(oper);
  num_operators += 1;
}


double Expression::evaluate()
{
  for (int i=0; i<num_operators; ++i)
    {
      ((*operators)[i])->evaluate();
    }
  return ((*operators)[num_operators-1])->value;
}


void AddOperator::evaluate()
{
  value = arg1->value + arg2->value;
}


void SubtractOperator::evaluate()
{
  value = arg1->value - arg2->value;
}


void MultiplyOperator::evaluate()
{
  value = arg1->value * arg2->value;
}


void DivideOperator::evaluate()
{
  value = arg1->value / arg2->value;
}


void PowerOperator::evaluate()
{
  value = ::pow(arg1->value, arg2->value);
}


