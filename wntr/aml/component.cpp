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


std::shared_ptr<std::unordered_map<Leaf*, double> > Constraint::rad()
{
  for (int i=0; i<num_conditions; ++i)
    {
      if (conditions[i]->evaluate() <= 0)
	{
	  return exprs[i]->rad();
	}
    }
  return exprs[num_conditions]->rad();
}


std::shared_ptr<std::unordered_set<Var*> > Constraint::get_vars()
{
  if (num_conditions == 0)
    {
      return exprs[0]->get_vars();
    }
  std::shared_ptr<std::unordered_set<Var*> > vars = std::make_shared<std::unordered_set<Var*> >();
  std::shared_ptr<std::unordered_set<Var*> > _vars;
  for (int i=0; i<num_conditions; ++i)
    {
      _vars = exprs[i]->get_vars();
      for (auto &v : *_vars)
	{
	  vars->insert(v);
	}
    }
  return vars;
}


std::vector<Var*> Constraint::py_get_vars()
{
  std::vector<Var*> vars;
  std::shared_ptr<std::unordered_set<Var*> > _vars = get_vars();
  for (auto &_v : *_vars)
    {
      vars.push_back(_v);
    }
  return vars;
}


double Constraint::ad(Var* v)
{
  std::shared_ptr<std::unordered_map<Leaf*, double> > ders = rad();
  return (*ders)[v];
}
