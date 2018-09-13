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


std::shared_ptr<std::vector<std::shared_ptr<Operator> > > ExpressionBase::get_operators()
{
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > ops = std::make_shared<std::vector<std::shared_ptr<Operator> > >();
  return ops;
}


std::shared_ptr<std::vector<std::shared_ptr<Var> > > ExpressionBase::get_vars()
{
  std::shared_ptr<std::vector<std::shared_ptr<Var> > > vars = std::make_shared<std::vector<std::shared_ptr<Var> > >();
  return vars;
}


void Expression::update_sparsity(std::shared_ptr<Node> n, std::shared_ptr<Operator> op)
{
  if (op != operators->back())
    {
      throw std::runtime_error("Expression::update_sparsity: sparsity can only be updated for the last operator added to the expression.");
    }
  std::shared_ptr<std::vector<std::shared_ptr<Var> > > vars = n->get_vars();
  int op_ndx = operators->size() - 1;
  for (std::shared_ptr<Var> &ptr_to_var : vars)
    {
      if ((*sparsity)[n].back() != op_ndx)
	{
	  (*sparsity)[n].push_back(op_ndx);
	}
    }
}


std::shared_ptr<ExpressionBase> Leaf::add_leaf(ExpressionBase &n, double coef)
{
  if (n.get_type() == "Float" && n.evaluate() == 0.0)
    {
      return shared_from_this();
    }
  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
  op->add_arg(shared_from_this(), 1.0);
  op->add_arg(n.shared_from_this(), coef);
  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
  expr->operators->push_back(op);
  expr->update_sparsity(shared_from_this(), op);
  expr->update_sparsity(n.shared_from_this(), op);
  return expr;
}


std::shared_ptr<ExpressionBase> Float::add_leaf(ExpressionBase &n, double coef)
{
  if (n.get_type() == "Float")
    {
      value += coef * n.evaluate();
      return shared_from_this();
    }
  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
  op->add_arg(shared_from_this(), 1.0);
  op->add_arg(n.shared_from_this(), coef);
  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
  expr->operators->push_back(op);
  expr->update_sparsity(shared_from_this(), op);
  expr->update_sparsity(n.shared_from_this(), op);
  return expr;
}


std::shared_ptr<ExpressionBase> Expression::add_leaf(ExpressionBase &n, double coef)
{
  if (n.get_type() == "Float" && n.evaluate() == 0.0)
    {
      return shared_from_this();
    }
  std::shared_ptr<Operator> last_operator = operators->back();
  if (last_operator->get_type() == "SummationOperator")
    {
      last_operator->add_arg(n.shared_from_this(), coef);
      update_sparsity(n.shared_from_this(), last_operator);
      return shared_from_this();
    }
  else
    {
      std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
      op->add_arg(last_operator, 1.0);
      op->add_arg(n.shared_from_this(), coef);
      operators->push_back(op);
      
	  return n1.shared_from_this();
	}  
}


std::shared_ptr<ExpressionBase> summation_helper(ExpressionBase &n1, ExpressionBase &n2, double n2_coef)
{
  if (leaf_types.count(n1.get_type()) && leaf_types.count(n2.get_type()))  // both are leaves
    {
      if (n1.get_type() == "Float" && n1.evaluate() == 0.0)
	{
	  return n2 * n2_coef;
	}
      else if (n2.get_type() == "Float" && n2.evaluate() == 0.0)
	{
	  return n1.shared_from_this();
	}
      else
	{
	  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
	  op->add_arg(n1.shared_from_this(), 1.0);
	  op->add_arg(n2.shared_from_this(), n2_coef);
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->add_operator(op);
	  return expr;
	}
    }
  else if ((!leaf_types.count(n1.get_type())) && (!leaf_types.count(n2.get_type())))  // neither are leaves
    {
      std::shared_ptr<Operator> n1_last_operator = n1.get_last_operator();
      std::shared_ptr<Operator> n2_last_operator = n2.get_last_operator();
      if (n1_last_operator->get_type() == "SummationOperator" && n2_last_operator->get_type() == "SummationOperator")
	{
	  n1.remove_last_operator();
	  n2.remove_last_operator();
	  std::shared_ptr<std::vector<std::shared_ptr<Node> > > n2_last_operator_args = n2_last_operator->get_args();
	  for (std::shared_ptr<Node> &ptr_to_arg : (*n2_last_operator_args))
	    {
	      n1_last_operator->add_arg(ptr_to_arg, n2_coef);
	    }
	  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > n2_operators = n2.get_operators();
	  for (std::shared_ptr<Operator> &_op : *n2_operators)
	    {
	      n1.add_operator(_op);
	    }
	  n1.add_operator(n1_last_operator);
	  return n1.shared_from_this();
	}
      else if (n1_last_operator->get_type() != "SummationOperator" && n2_last_operator->get_type() != "SummationOperator")
	{
	  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > n2_operators = n2.get_operators();
	  for (std::shared_ptr<Operator> &_op : n2_operators)
	    {
	      n1.add_operator(_op);
	    }
	  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
	  op->add_arg(n1_last_operator, 1.0);
	  op->add_arg(n2_last_operator, n2_coef);
	  n1.add_operator(op);
	  return n1.shared_from_this();
	}
      else if (n1_last_operator->get_type() == "SummationOperator")
	{
	  n1_last_operator->add_arg(n2_last_operator, n2_coef);
	  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > n1_operators = n1.get_operators();
	  for (std::shared_ptr<Operator> &_op : *n1_operators)
	    {
	      n2.add_operator(_op);
	    }
	  return n2.shared_from_this();
	}
      else
	{
	  n2_last_operator->multiply_const(n2_coef);
	  n2_last_operator->add_arg(n1_last_operator, 1.0);
	  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > n2_operators = n2.get_operators();
	  for (std::shared_ptr<Operator> &_op : *n2_operators)
	    {
	      n1.add_operator(_op);
	    }
	  return n1.shared_from_this();
	}
    }
  else if (leaf_types.count(n1.get_type()))  // n1 is a leaf, but n2 is an expression
    {
      if (n1.get_type() == "Float" && n1.evaluate() == 0.0)
	{
	  return n2 * n2_coef;
	}
      std::shared_ptr<Operator> n2_last_operator = n2.get_last_operator();
      if (n2_last_operator->get_type() == "SummationOperator")
	{
	  n2.remove_last_operator();
	  n2_last_operator->multiply_const(n2_coef);
	  n2_last_operator->add_arg(n1, 1.0);
	  n2.add_operator(n2_last_operator);
	  return n2.shared_from_this();
	}
      else
	{
	  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
	  op->add_arg(n1, 1.0);
	  op->add_arg(n2_last_operator, n2_coef);
	  n2.add_operator(op);
	  return n2.shared_from_this();
	}
    }
  else  // n2 is a leaf, but n1 is an expression
    {
      if (n2.get_type() == "Float" && n2.evaluate() == 0.0)
	{
	  return n1.shared_from_this();
	}
      std::shared_ptr<Operator> n1_last_operator = n1.get_last_operator();
      if (n1_last_operator->get_type() == "SummationOperator")
	{
	  n1.remove_last_operator();
	  n1_last_operator->add_arg(n2, n2_coef);
	  n1.add_operator(n1_last_operator);
	  return n1.shared_from_this();
	}
      else
	{
	  std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
	  op->add_arg(n1_last_operator, 1.0);
	  op->add_arg(n2, n2_coef);
	  n1.add_operator(op);
	  return n1.shared_from_this();
	}
    }
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator+(ExpressionBase& n)
{
  return summation_helper(*this, n, 1)
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator-(ExpressionBase& n)
{
  return summation_helper(*this, n, -1)
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator*(ExpressionBase& n)
{
  if (get_type() == "Float" && evaluate() == 0.0)
    {
      return n.shared_from_this();
    }
  else if (n.get_type() == "Float" && n.evaluate() == 0.0)
    {
      return shared_from_this();
    }
  else
    {
      std::shared_ptr<Node> arg1 = get_last_operator();
      std::shared_ptr<Node> arg2 = n.get_last_operator();
      std::shared_ptr<MultiplyOperator> op = std::make_shared<MultiplyOperator>(arg1, arg2);
      
    }
}
