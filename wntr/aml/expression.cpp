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

int ExpressionBase::get_num_operators()
{
  return 0;
}


std::shared_ptr<Expression> clone_expr_shallow(ExpressionBase &expr)
{
  std::shared_ptr<Expression> new_expr = std::make_shared<Expression>();
  int num_operators = expr.get_num_operators();
  std::shared_ptr<std::vector<std::shard_ptr<Operator> > > operators = expr.get_operators();
  for (int i=0; i<num_operators; ++i)
    {
      new_expr->add_operator(operators[i]);
    }
  return new_expr;
}


std::shared_ptr<ExpressionBase> summation_helper(ExpressionBase &n1, ExpressionBase &n2, double n2_coef)
{
  if (leaf_types.count(n1.get_type()))
    {
      if (n1.get_type() == "Float" && n1.evaluate() == 0.0)
	{
	  return n2 * n2_coef;
	}
      else if (leaf_types.count(n2.get_type()))
	{
	  if (n2.get_type() == "Float" && n2.evaluate() == 0.0)
	    {
	      return n1.shared_from_this();
	    }
	  else
	    {
	      std::shared_ptr<SummationOperator> op = std::make_shared<SummationOperator>();
	      op->add_arg(n1, 1.0);
	      op->add_arg(n2, n2_coef);
	      std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	      expr->add_operator(op);
	      return expr;
	    }
	}
      else
	{
	  if (n2.get_operators()->size() != n2.get_num_operators())
	    {
	      std::shared_ptr<Expression> expr = clone_expr_shallow(n2);
	    }
	  else
	    {
	      std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	      expr->set_operators(n2.get_operators());
	      expr->set_sparsity(n2.get_sparsity());
	    }
	  std::shared_ptr<Operator> op = expr->get_last_operator();
	  if (op->get_type() == "SummationOperator")
	    {
	      op->multiply_const(n2_coef);
	      op->add_arg(n1, 1.0);
	      expr->update_sparsity(op, n1);
	      return expr;
	    }
	  else
	    {
	      std::shared_ptr<SummationOperator> new_op = std::make_shared<SummationOperator>();
	      new_op->add_arg(n1, 1.0);
	      new_op->add_arg(op, n2_coef);
	      expr->add_operator(new_op);
	      return expr;
	    }
	}
    }
  else
    {
      if (n2.get_type() == "Float" && n2.evaluate() == 0.0)
	{
	  return n1.shared_from_this();
	}
      else
	{
	  if (n1.get_operators()->size() != n1.get_num_operators())
	    {
	      std::shared_ptr<Expression> expr = clone_expr_shallow(n1);
	    }
	  else
	    {
	      std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	      expr->set_operators(n1.get_operators());
	      expr->set_sparsity(n1.get_sparsity());
	    }
	  if (leaf_types.count(n2.get_type()))
	    {
	      
	    }
	}
    }
}


std::shared_ptr<ExpressionBase> ExpressionBase::operator+(ExpressionBase& n)
{
  
}
