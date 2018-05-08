#include "aml_tnlp.hpp"
using namespace Ipopt;


std::shared_ptr<IpoptConstraint> create_ipopt_constraint(std::shared_ptr<Node> n)
{
  std::shared_ptr<IpoptConstraint> c = std::make_shared<IpoptConstraint>();
  c->expr = n;
  return c;
}


std::shared_ptr<IpoptObjective> create_ipopt_objective(std::shared_ptr<Node> n)
{
  std::shared_ptr<IpoptObjective> o = std::make_shared<IpoptObjective>();
  o->expr = n;
  return o;
}


void IpoptModel::add_var(std::shared_ptr<Var> v)
{
  vars.push_back(v);
}


void IpoptModel::remove_var(std::shared_ptr<Var> v)
{
  auto it = vars.begin();
  std::advance(it, v->index);
  vars.erase(it);
}


void IpoptModel::set_objective(std::shared_ptr<IpoptObjective> new_obj)
{
  if (obj != nullptr)
    {
      auto obj_vars = obj->expr->get_vars();
      for (auto ptr_to_var1 : (*obj_vars))
	{
          for (auto ptr_to_var2 : (*obj_vars))
	    {
              if (ptr_to_var2->index <= ptr_to_var1->index)
		{
                  if (obj->expr->has_ad2(*ptr_to_var1, *ptr_to_var2))
		    {
                      hessian_map[ptr_to_var1][ptr_to_var2]["obj"].erase(obj);
                      if (hessian_map[ptr_to_var1][ptr_to_var2]["cons"].size() == 0 &&
                          hessian_map[ptr_to_var1][ptr_to_var2]["obj"].size() == 0)
			{
                          hessian_map[ptr_to_var1].erase(ptr_to_var2);
			}
                      if (hessian_map[ptr_to_var1].size() == 0)
			{
                          hessian_map.erase(ptr_to_var1);
			}
		    }
		}
	    }
	}
    }
  obj = new_obj;
  auto obj_vars = obj->expr->get_vars();
  for (auto ptr_to_var1 : (*obj_vars))
    {
      for (auto ptr_to_var2 : (*obj_vars))
	{
          if (ptr_to_var2->index <= ptr_to_var1->index)
	    {
              if (obj->expr->has_ad2(*ptr_to_var1, *ptr_to_var2))
		{
                  hessian_map[ptr_to_var1][ptr_to_var2]["obj"].insert(obj);
		}
	    }
	}
    }
}


void IpoptModel::add_constraint(std::shared_ptr<IpoptConstraint> con)
{
  cons.push_back(con);
  auto con_vars = con->expr->get_vars();
  for (auto ptr_to_var1 : (*con_vars))
  {
      for (auto ptr_to_var2 : (*con_vars))
      {
          if (ptr_to_var2->index <= ptr_to_var1->index)
          {
              if (con->expr->has_ad2(*ptr_to_var1, *ptr_to_var2))
              {
                  hessian_map[ptr_to_var1][ptr_to_var2]["cons"].insert(con);
              }
          }
      }
  }
}


void IpoptModel::remove_constraint(std::shared_ptr<IpoptConstraint> con)
{
  auto it = cons.begin();
  std::advance(it, con->index);
  cons.erase(it);

  auto con_vars = con->expr->get_vars();
  for (auto ptr_to_var1 : (*con_vars))
  {
      for (auto ptr_to_var2 : (*con_vars))
      {
          if (ptr_to_var2->index <= ptr_to_var1->index)
          {
              if (con->expr->has_ad2(*ptr_to_var1, *ptr_to_var2))
              {
                  hessian_map[ptr_to_var1][ptr_to_var2]["cons"].erase(con);
                  if (hessian_map[ptr_to_var1][ptr_to_var2]["cons"].size() == 0 &&
                      hessian_map[ptr_to_var1][ptr_to_var2]["obj"].size() == 0)
                  {
                      hessian_map[ptr_to_var1].erase(ptr_to_var2);
                  }
                  if (hessian_map[ptr_to_var1].size() == 0)
                  {
                      hessian_map.erase(ptr_to_var1);
                  }
              }
          }
      }
  }
}


void IpoptModel::solve()
{
  SmartPtr<AML_NLP> mynlp = new AML_NLP();
  mynlp->set_model(this);

  SmartPtr<IpoptApplication> app = IpoptApplicationFactory();
  app->RethrowNonIpoptException(true);

  ApplicationReturnStatus status;
  status = app->Initialize();
  status = app->OptimizeTNLP(mynlp);
}


std::string IpoptConstraint::_print()
{
  return expr->_print();
}


std::shared_ptr<std::set<std::shared_ptr<Var>>> IpoptConstraint::get_vars()
{
  return expr->get_vars();
}


double IpoptConstraint::evaluate()
{
  return expr->evaluate();
}


double IpoptConstraint::ad(Var &n, bool new_eval)
{
  return expr->ad(n, new_eval);
}


double IpoptConstraint::ad2(Var &n1, Var &n2, bool new_eval)
{
  return expr->ad2(n1, n2, new_eval);
}


double IpoptConstraint::get_dual()
{
  return dual;
}
