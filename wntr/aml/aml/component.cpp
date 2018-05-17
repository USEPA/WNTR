#include "component.hpp"


std::shared_ptr<Constraint> create_constraint(std::shared_ptr<Node> expr, double lb, double ub)
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


std::shared_ptr<Objective> create_objective(std::shared_ptr<Node> n)
{
  std::shared_ptr<Objective> o = std::make_shared<Objective>();
  o->expr = n;
  return o;
}


std::string Constraint::_print()
{
  return expr->_print();
}


std::string Objective::_print()
{
  return expr->_print();
}


std::string ConditionalConstraint::_print()
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
      s += (*condition_iterator)->_print();
      s += " <= 0:\n";
      s += "\t";
      s += (*expr_iterator)->_print();
      s += "\n";
      ++condition_iterator;
      ++expr_iterator;
      ++i;
    }
  s += "else: \n";
  s += "\t";
  s += (*expr_iterator)->_print();
  s += "\n";
  return s;
}


std::shared_ptr<std::set<std::shared_ptr<Var> > > Objective::get_vars()
{
  return expr->get_vars();
}


std::shared_ptr<std::set<std::shared_ptr<Var> > > Constraint::get_vars()
{
  return expr->get_vars();
}


std::shared_ptr<std::set<std::shared_ptr<Var> > > ConditionalConstraint::get_vars()
{
  std::shared_ptr<std::set<std::shared_ptr<Var> > > vs = std::make_shared<std::set<std::shared_ptr<Var> > >();
  std::shared_ptr<std::set<std::shared_ptr<Var> > > _vars = std::make_shared<std::set<std::shared_ptr<Var> > >();
  for (auto &e : exprs)
    {
      _vars = e->get_vars();
      for (auto &ptr_to_var : (*_vars))
        {
     	  vs->insert(ptr_to_var);
        }
    }
  return vs;
}


double Constraint::evaluate()
{
  value = expr->evaluate();
  return value;
}


double Constraint::ad(Var &n, bool new_eval)
{
  return expr->ad(n, new_eval);
}


double Constraint::ad2(Var &n1, Var &n2, bool new_eval)
{
  return expr->ad2(n1, n2, new_eval);
}


double Objective::evaluate()
{
  value = expr->evaluate();
  return value;
}


double Objective::ad(Var &n, bool new_eval)
{
  return expr->ad(n, new_eval);
}


double Objective::ad2(Var &n1, Var &n2, bool new_eval)
{
  return expr->ad2(n1, n2, new_eval);
}


void ConditionalConstraint::add_condition(std::shared_ptr<Node> condition, std::shared_ptr<Node> expr)
{
  condition_exprs.push_back(condition);
  exprs.push_back(expr);
}


void ConditionalConstraint::add_final_expr(std::shared_ptr<Node> expr)
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
      value = (*expr_iter)->evaluate();
      found = true;
      break;
    }
    ++condition_iter;
    ++ expr_iter;
  }
  if (!found)
  {
    value = (*expr_iter)->evaluate();
  }
  return value;
}


double ConditionalConstraint::ad(Var &n, bool new_eval)
{
  auto condition_iter = condition_exprs.begin();
  auto expr_iter = exprs.begin();
  
  while (condition_iter != condition_exprs.end())
    {
      if ((*condition_iter)->evaluate() <= 0)
        {
	  return (*expr_iter)->ad(n, new_eval);
        }
      ++condition_iter;
      ++ expr_iter;
    }
  return (*expr_iter)->ad(n, new_eval);
}


double ConditionalConstraint::ad2(Var &n1, Var &n2, bool new_eval)
{
  auto condition_iter = condition_exprs.begin();
  auto expr_iter = exprs.begin();

  while (condition_iter != condition_exprs.end())
    {
      if ((*condition_iter)->evaluate() <= 0)
        {
	  return (*expr_iter)->ad2(n1, n2, new_eval);
        }
      ++condition_iter;
      ++ expr_iter;
    }
  return (*expr_iter)->ad2(n1, n2, new_eval);
}


double Constraint::get_dual()
{
  return dual;
}


double ConditionalConstraint::get_dual()
{
  return dual;
}


bool Constraint::has_ad2(Var &n1, Var &n2)
{
  return expr->has_ad2(n1, n2);
}


bool Objective::has_ad2(Var &n1, Var &n2)
{
  return expr->has_ad2(n1, n2);
}


bool ConditionalConstraint::has_ad2(Var &n1, Var &n2)
{
  auto expr_iter = exprs.begin();

  while (expr_iter != exprs.end())
    {
      if ((*expr_iter)->has_ad2(n1, n2))
      {
	    return true;
	  }
      ++ expr_iter;
    }
  if ((*expr_iter)->has_ad2(n1, n2))
  {
    return true;
  }
  return false;
}


