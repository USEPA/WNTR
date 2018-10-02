#include "component.hpp"


void ConditionalExpression::add_condition(ExpressionBase* condition, ExpressionBase* expr)
{
  assert (conditions.size() == exprs.size());
  if (condition->is_leaf())
    {
      conditions.push_back(condition);
    }
  else
    {
      conditions.push_back(dynamic_cast<Expression*>(condition)->copy());
    }
  if (expr->is_leaf())
    {
      exprs.push_back(expr);
    }
  else
    {
      exprs.push_back(dynamic_cast<Expression*>(expr)->copy());
    }
}


void ConditionalExpression::add_final_expr(ExpressionBase* expr)
{
  if (expr->is_leaf())
    {
      exprs.push_back(expr);
    }
  else
    {
      exprs.push_back(dynamic_cast<Expression*>(expr)->copy());
    }
}


ConditionalExpression::~ConditionalExpression()
{
  for (auto &_condition : conditions)
    {
      if (_condition->is_expr())
	{
	  delete _condition;
	}
    }
  for (auto &_expr : exprs)
    {
      if (_expr->is_expr())
	{
	  delete _expr;
	}
    }
}


Constraint::Constraint(ExpressionBase* expr)
{
  conditions = new Evaluator*[0];
  exprs = new Evaluator*[1];
  exprs[0] = new Evaluator(expr);
  set_vars();
}


Constraint::Constraint(ConditionalExpression* conditional_expr)
{
  conditions = new Evaluator*[conditional_expr->conditions.size()];
  exprs = new Evaluator*[conditional_expr->exprs.size()];
  for (int i=0; i<conditional_expr->conditions.size(); ++i)
    {
      conditions[i] = new Evaluator(conditional_expr->conditions[i]);
      exprs[i] = new Evaluator(conditional_expr->exprs[i]);
      num_conditions += 1;
    }
  exprs[num_conditions] = new Evaluator(conditional_expr->exprs[num_conditions]);
  set_vars();
}


void Constraint::set_vars()
{
  std::unordered_set<Var*> vars_set;
  std::shared_ptr<std::vector<Var*> > _vars;
  for (int i=0; i<=num_conditions; ++i)
    {
      _vars = exprs[i]->get_vars();
      for (Var* &v: *_vars)
	{
	  vars_set.insert(v);
	}
    }
  num_vars = vars_set.size();
  vars = new Var*[num_vars];
  int i = 0;
  for (auto &v : vars_set)
    {
      vars[i] = v;
      ++i;
    }
}


Constraint::~Constraint()
{
  for (int i=0; i<num_conditions; ++i)
    {
      delete conditions[i];
      delete exprs[i];
    }
  delete exprs[num_conditions];
  delete conditions;
  delete exprs;
}


double Constraint::evaluate()
{
  for (int i=0; i<num_conditions; ++i)
    {
      if (conditions[i]->evaluate() <= 0)
	{
	  return exprs[i]->evaluate();
	}
    }
  return exprs[num_conditions]->evaluate();
}


std::string Constraint::__str__()
{
  if (num_conditions == 0)
    {
      return exprs[0]->__str__();
    }
  
  std::string s = "";
  for (int i=0; i<num_conditions; ++i)
    {
      if (i == 0)
	{
	  s += "if ";
	}
      else
	{
	  s += "elif ";
	}
      s += conditions[i]->__str__();
      s += " <= 0:\n\t";
      s += exprs[i]->__str__();
      s += "\n";
    }
  s += "else: \n\t";
  s += exprs[num_conditions]->__str__();
  s += "\n";
  return s;
}


void Constraint::rad()
{
  for (int i=0; i<num_vars; ++i)
    {
      vars[i]->der = 0.0;
    }
  bool found = false;
  for (int i=0; i<num_conditions; ++i)
    {
      if (conditions[i]->evaluate() <= 0)
	{
	  exprs[i]->rad();
	  found = true;
	  break;
	}
    }
  if (!found)
    {
      exprs[num_conditions]->rad();
    }
}


std::vector<Var*> Constraint::py_get_vars()
{
  std::vector<Var*> vars_vector;
  for (int i=0; i<num_vars; ++i)
    {
      vars_vector.push_back(vars[i]);
    }
  return vars_vector;
}


std::unordered_set<Var*> Constraint::get_var_set()
{
  std::unordered_set<Var*> var_set;
  for (int i=0; i<num_vars; ++i)
    {
      var_set.insert(vars[i]);
    }
  return var_set;
}


double Constraint::ad(Var* v)
{
  if (!(get_var_set().count(v)))
    {
      return 0.0;
    }
  rad();
  return v->der;
}
