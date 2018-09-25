#include "expression.hpp"


Expression::~Expression()
{
  Float *f;
  for (int i=0; i<num_floats; ++i)
    {
      f = (*floats)[i];
      f->refcount -= 1;
      if (f->refcount == 0)
	{
	  delete f;
	}
    }
}


void Expression::add_leaf(Leaf* leaf)
{
  if (!(leaf_to_ndx_map->count(leaf)))
    {
      leaves->push_back(leaf);
      (*leaf_to_ndx_map)[leaf] = num_leaves;
      num_leaves += 1;

      if (leaf->is_float())
	{
	  Float *f = dynamic_cast<Float*>(leaf);
	  f->refcount += 1;
	  floats->push_back(f);
	  num_floats += 1;
	}
    }  
}


Expression* Expression::copy()
{
  Expression* new_expr = new Expression();
  for (int i=0; i < num_operators; ++i)
    {
      new_expr->operators->push_back((*operators)[i]);
      new_expr->args1->push_back((*args1)[i]);
      new_expr->args2->push_back((*args2)[i]);
      new_expr->num_operators += 1;
    }
  Leaf* leaf;
  for (int i=0; i < num_leaves; ++i)
    {
      leaf = (*leaves)[i];
      new_expr->add_leaf(leaf);
    }
  return new_expr;
}


Expression* _expr_copy(Expression* expr)
{
  Expression* new_expr;
  if ((int) (expr->operators->size()) != expr->num_operators)
    {
      new_expr = expr->copy();
    }
  else
    {
      new_expr = new Expression();
      new_expr->operators = expr->operators;
      new_expr->args1 = expr->args1;
      new_expr->args2 = expr->args2;
      new_expr->leaves = expr->leaves;
      new_expr->leaf_to_ndx_map = expr->leaf_to_ndx_map;
      new_expr->floats = expr->floats;
      new_expr->num_operators = expr->num_operators;
      new_expr->num_leaves = expr->num_leaves;
      new_expr->num_floats = expr->num_floats;
      Float* f;
      for (int i=0; i<new_expr->num_floats; ++i)
	{
	  f = (*(new_expr->floats))[i];
	  f->refcount += 1;
	}
    }
  return new_expr;
}


int _arg_ndx_to_operator_ndx(int arg_ndx)
{
  return (-arg_ndx) - 1;
}


int _operator_ndx_to_arg_ndx(int operator_ndx)
{
  return -(operator_ndx + 1);
}


ExpressionBase *binary_helper(Expression *n1, Expression *n2, const short operation)
{
  Expression *expr = _expr_copy(n1);
  Leaf* leaf;
  for (int i=0; i<n2->num_leaves; ++i)
    {
      leaf = (*(n2->leaves))[i];
      expr->add_leaf(leaf);
    }
  int _arg1;
  int _arg2;
  for (int i=0; i<n2->num_operators; ++i)
    {
      expr->operators->push_back((*(n2->operators))[i]);
      _arg1 = (*(n2->args1))[i];
      _arg2 = (*(n2->args2))[i];
      if (_arg1 < 0)
	{
	  expr->args1->push_back(_operator_ndx_to_arg_ndx(n1->num_operators + _arg_ndx_to_operator_ndx(_arg1)));
	}
      else
	{
	  expr->args1->push_back((*(expr->leaf_to_ndx_map))[(*(n2->leaves))[_arg1]]);
	}
      if (_arg2 < 0)
	{
	  expr->args2->push_back(_operator_ndx_to_arg_ndx(n1->num_operators + _arg_ndx_to_operator_ndx(_arg2)));
	}
      else
	{
	  expr->args2->push_back((*(expr->leaf_to_ndx_map))[(*(n2->leaves))[_arg2]]);
	}
      expr->num_operators += 1;
    }
  expr->operators->push_back(operation);
  expr->args1->push_back(_operator_ndx_to_arg_ndx(n1->num_operators - 1));
  expr->args2->push_back(_operator_ndx_to_arg_ndx(n1->num_operators + n2->num_operators - 1));
  expr->num_operators += 1;
  return expr;
}


ExpressionBase *binary_helper(Expression *n1, Leaf *n2, const short operation)
{
  Expression* expr = _expr_copy(n1);
  expr->operators->push_back(operation);
  expr->add_leaf(n2);
  expr->args1->push_back(_operator_ndx_to_arg_ndx(n1->num_operators - 1));
  expr->args2->push_back((*(expr->leaf_to_ndx_map))[n2]);
  expr->num_operators += 1;
  return expr;
}


ExpressionBase *binary_helper(Leaf *n1, Expression *n2, const short operation)
{
  Expression* expr = _expr_copy(n2);
  expr->operators->push_back(operation);
  expr->add_leaf(n1);
  expr->args1->push_back((*(expr->leaf_to_ndx_map))[n1]);
  expr->args2->push_back(_operator_ndx_to_arg_ndx(n2->num_operators - 1));
  expr->num_operators += 1;
  return expr;
}


ExpressionBase *binary_helper(Leaf *n1, Leaf *n2, const short operation)
{
  Expression *expr = new Expression();
  expr->operators->push_back(operation);

  expr->add_leaf(n1);
  expr->add_leaf(n2);
  expr->args1->push_back((*(expr->leaf_to_ndx_map))[n1]);
  expr->args2->push_back((*(expr->leaf_to_ndx_map))[n2]);
  expr->num_operators += 1;
  return expr;
}


ExpressionBase* binary_helper2(ExpressionBase *n1, ExpressionBase *n2, const short operation)
{
  if (n1->is_leaf() && n2->is_leaf())
    {
      return binary_helper(dynamic_cast<Leaf*>(n1), dynamic_cast<Leaf*>(n2), operation);
    }
  else if (n1->is_leaf())
    {
      return binary_helper(dynamic_cast<Leaf*>(n1), dynamic_cast<Expression*>(n2), operation);
    }
  else if (n2->is_leaf())
    {
      return binary_helper(dynamic_cast<Expression*>(n1), dynamic_cast<Leaf*>(n2), operation);
    }
  else
    {
      return binary_helper(dynamic_cast<Expression*>(n1), dynamic_cast<Expression*>(n2), operation);
    }
}


ExpressionBase* ExpressionBase::operator+(ExpressionBase& n)
{
  return binary_helper2(this, &n, ADD);
}


ExpressionBase* ExpressionBase::operator-(ExpressionBase& n)
{
  return binary_helper2(this, &n, SUBTRACT);
}


ExpressionBase* ExpressionBase::operator*(ExpressionBase& n)
{
  return binary_helper2(this, &n, MULTIPLY);
}


ExpressionBase* ExpressionBase::operator/(ExpressionBase& n)
{
  return binary_helper2(this, &n, DIVIDE);
}


ExpressionBase* ExpressionBase::__pow__(ExpressionBase& n)
{
  return binary_helper2(this, &n, POWER);
}


ExpressionBase* ExpressionBase::operator-()
{
  Float *f = new Float(0.0);
  return (*f) - (*this);
}


ExpressionBase* ExpressionBase::operator+(double n)
{
  Float* f = new Float(n);
  return (*this) + (*f);
}


ExpressionBase* ExpressionBase::operator-(double n)
{
  Float* f = new Float(n);
  return (*this) - (*f);
}


ExpressionBase* ExpressionBase::operator*(double n)
{
  Float* f = new Float(n);
  return (*this) * (*f);
}


ExpressionBase* ExpressionBase::operator/(double n)
{
  Float* f = new Float(n);
  return (*this) / (*f);
}


ExpressionBase* ExpressionBase::__pow__(double n)
{
  Float* f = new Float(n);
  return __pow__(*f);
}


ExpressionBase* ExpressionBase::__radd__(double n)
{
  Float* f = new Float(n);
  return (*f) + (*this);
}


ExpressionBase* ExpressionBase::__rsub__(double n)
{
  Float* f = new Float(n);
  return (*f) - (*this);
}


ExpressionBase* ExpressionBase::__rmul__(double n)
{
  Float* f = new Float(n);
  return (*f) * (*this);
}


ExpressionBase* ExpressionBase::__rdiv__(double n)
{
  Float* f = new Float(n);
  return (*f) / (*this);
}


ExpressionBase* ExpressionBase::__rtruediv__(double n)
{
  Float* f = new Float(n);
  return (*f) / (*this);
}


ExpressionBase* ExpressionBase::__rpow__(double n)
{
  Float* f = new Float(n);
  return f->__pow__(*this);
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


bool Leaf::is_leaf()
{
  return true;
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


bool Expression::is_expr()
{
  return true;
}


std::string Expression::__str__()
{
  return "not implemented yet";
}
