#include "component.hpp"


std::unordered_set<std::shared_ptr<ExpressionBase> > Component::py_get_vars()
{
  return *(get_vars());
}


std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > Objective::get_vars()
{
  return expr->get_vars();
}


std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > Constraint::get_vars()
{
  return expr->get_vars();
}


std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > ConditionalConstraint::get_vars()
{
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > all_vars;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > e_vars;
  for (auto &e : exprs)
    {
      e_vars = e->get_vars();
      for (auto &v : (*e_vars))
	{
	  all_vars->insert(v);
	}
    }
  return all_vars;
}


std::shared_ptr<Constraint> create_constraint(std::shared_ptr<ExpressionBase> expr, double lb, double ub)
{
  std::shared_ptr<Constraint> c = std::make_shared<Constraint>();
  c->expr = expr;
  c->lb = lb;
  c->ub = ub;
  return c;
}


std::shared_ptr<ConditionalConstraint> create_conditional_constraint(double lb, double ub)
{
  std::shared_ptr<ConditionalConstraint> c = std::make_shared<ConditionalConstraint>();
  c->lb = lb;
  c->ub = ub;
  return c;
}


std::shared_ptr<Objective> create_objective(std::shared_ptr<ExpressionBase> n)
{
  std::shared_ptr<Objective> o = std::make_shared<Objective>();
  o->expr = n;
  return o;
}


std::string Constraint::__str__()
{
  return expr->__str__();
}


std::string Objective::__str__()
{
  return expr->__str__();
}


std::string ConditionalConstraint::__str__()
{
  std::string s = "";
  auto condition_iterator = condition_exprs.begin();
  auto expr_iterator = exprs.begin();
  int i = 0;
  
  while (condition_iterator != condition_exprs.end() && expr_iterator != exprs.end())
    {
      if (i == 0)
        {
	  s += "if ";
        }
      else
        {
	  s += "elif ";
        }
      s += (*condition_iterator)->__str__();
      s += " <= 0:\n";
      s += "\t";
      s += (*expr_iterator)->__str__();
      s += "\n";
      ++condition_iterator;
      ++expr_iterator;
      ++i;
    }
  s += "else: \n";
  s += "\t";
  s += (*expr_iterator)->__str__();
  s += "\n";
  return s;
}


double Constraint::evaluate()
{
  return expr->evaluate();
}


double Objective::evaluate()
{
  return expr->evaluate();
}


void ConditionalConstraint::add_condition(std::shared_ptr<ExpressionBase> condition, std::shared_ptr<ExpressionBase> expr)
{
  condition_exprs.push_back(condition);
  exprs.push_back(expr);
}


void ConditionalConstraint::add_final_expr(std::shared_ptr<ExpressionBase> expr)
{
  exprs.push_back(expr);
}


double ConditionalConstraint::evaluate()
{
  auto condition_iter = condition_exprs.begin();
  auto expr_iter = exprs.begin();
  bool found = false;
  
  while (condition_iter != condition_exprs.end())
    {
      if ((*condition_iter)->evaluate() <= 0)
	{
	  return (*expr_iter)->evaluate();
	}
      ++condition_iter;
      ++ expr_iter;
    }
  return (*expr_iter)->evaluate();
}


void Objective::rad(bool new_eval)
{
  expr->rad(new_eval);
}


void Constraint::rad(bool new_eval)
{
  expr->rad(new_eval);
}


void ConditionalConstraint::rad(bool new_eval)
{
  auto condition_iter = condition_exprs.begin();
  auto expr_iter = exprs.begin();
  bool found = false;
  
  while (condition_iter != condition_exprs.end())
    {
      if ((*condition_iter)->evaluate() <= 0)
        {
	  found = true;
	  (*expr_iter)->rad(new_eval);
        }
      ++condition_iter;
      ++ expr_iter;
    }
  if (!found)
    {
      (*expr_iter)->rad(new_eval);
    }
}


double Constraint::get_dual()
{
  return dual;
}


double ConditionalConstraint::get_dual()
{
  return dual;
}
