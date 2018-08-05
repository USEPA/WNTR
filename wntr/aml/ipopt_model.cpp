#include "aml_tnlp.hpp"
using namespace Ipopt;


void IpoptModel::add_var(std::shared_ptr<Var> v)
{
  vars.insert(v);
}


void IpoptModel::remove_var(std::shared_ptr<Var> v)
{
  vars.erase(v);
}


void IpoptModel::set_objective(std::shared_ptr<Objective> new_obj)
{
  if (obj != nullptr)
    {
      auto var_iter1 = obj->get_vars()->begin();
      auto var_iter2 = var_iter1;
      auto var_end_iter = obj->get_vars()->end();
      std::shared_ptr<Var> ptr_to_var1;
      std::shared_ptr<Var> ptr_to_var2;
      while (var_iter1 != var_end_iter)
	{
	  var_iter2 = var_iter1;
	  ptr_to_var1 = *var_iter1;
          while (var_iter2 != var_end_iter)
	    {
	      ptr_to_var2 = *var_iter2;
	      if (obj->has_ad2(*ptr_to_var1, *ptr_to_var2))
		{
		  hessian_map[ptr_to_var1][ptr_to_var2]["obj"].erase(obj);
		  hessian_map[ptr_to_var2][ptr_to_var1]["obj"].erase(obj);
		  if (hessian_map[ptr_to_var1][ptr_to_var2]["cons"].size() == 0 &&
		      hessian_map[ptr_to_var1][ptr_to_var2]["obj"].size() == 0)
		    {
		      hessian_map[ptr_to_var1].erase(ptr_to_var2);
		    }
		  if (hessian_map[ptr_to_var1].size() == 0)
		    {
		      hessian_map.erase(ptr_to_var1);
		    }
		  if (hessian_map[ptr_to_var2][ptr_to_var1]["cons"].size() == 0 &&
		      hessian_map[ptr_to_var2][ptr_to_var1]["obj"].size() == 0)
		    {
		      hessian_map[ptr_to_var2].erase(ptr_to_var1);
		    }
		  if (hessian_map[ptr_to_var2].size() == 0)
		    {
		      hessian_map.erase(ptr_to_var2);
		    }
		}
	      ++var_iter2;
	    }
	  ++var_iter1;
	}
    }
  obj = new_obj;
  auto var_iter1 = obj->get_vars()->begin();
  auto var_iter2 = var_iter1;
  auto var_end_iter = obj->get_vars()->end();
  std::shared_ptr<Var> ptr_to_var1;
  std::shared_ptr<Var> ptr_to_var2;
  while (var_iter1 != var_end_iter)
    {
      var_iter2 = var_iter1;
      ptr_to_var1 = *var_iter1;
      while (var_iter2 != var_end_iter)
	{
	  ptr_to_var2 = *var_iter2;
	  if (obj->has_ad2(*ptr_to_var1, *ptr_to_var2))
	    {
	      hessian_map[ptr_to_var1][ptr_to_var2]["obj"].insert(obj);
	      hessian_map[ptr_to_var2][ptr_to_var1]["obj"].insert(obj);
	    }
	  ++var_iter2;
	}
      ++var_iter1;
    }
}


void IpoptModel::add_constraint(std::shared_ptr<ConstraintBase> con)
{
  cons.insert(con);
  auto var_iter1 = con->get_vars()->begin();
  auto var_iter2 = var_iter1;
  auto var_end_iter = con->get_vars()->end();
  std::shared_ptr<Var> ptr_to_var1;
  std::shared_ptr<Var> ptr_to_var2;
  while (var_iter1 != var_end_iter)
    {
      var_iter2 = var_iter1;
      ptr_to_var1 = *var_iter1;
      while (var_iter2 != var_end_iter)
	{
	  ptr_to_var2 = *var_iter2;
	  if (con->has_ad2(*ptr_to_var1, *ptr_to_var2))
	    {
	      hessian_map[ptr_to_var1][ptr_to_var2]["cons"].insert(con);
	      hessian_map[ptr_to_var2][ptr_to_var1]["cons"].insert(con);
	    }
	  ++var_iter2;
	}
      ++var_iter1;
    }
}


void IpoptModel::remove_constraint(std::shared_ptr<ConstraintBase> con)
{
  cons.erase(con);
  auto var_iter1 = con->get_vars()->begin();
  auto var_iter2 = var_iter1;
  auto var_end_iter = con->get_vars()->end();
  std::shared_ptr<Var> ptr_to_var1;
  std::shared_ptr<Var> ptr_to_var2;
  while (var_iter1 != var_end_iter)
    {
      var_iter2 = var_iter1;
      ptr_to_var1 = *var_iter1;
      while (var_iter2 != var_end_iter)
	{
	  ptr_to_var2 = *var_iter2;
	  if (con->has_ad2(*ptr_to_var1, *ptr_to_var2))
	    {
	      hessian_map[ptr_to_var1][ptr_to_var2]["cons"].erase(con);
	      hessian_map[ptr_to_var2][ptr_to_var1]["cons"].erase(con);
	      if (hessian_map[ptr_to_var1][ptr_to_var2]["cons"].size() == 0 &&
		  hessian_map[ptr_to_var1][ptr_to_var2]["obj"].size() == 0)
		{
		  hessian_map[ptr_to_var1].erase(ptr_to_var2);
		}
	      if (hessian_map[ptr_to_var1].size() == 0)
		{
		  hessian_map.erase(ptr_to_var1);
		}
	      if (hessian_map[ptr_to_var2][ptr_to_var1]["cons"].size() == 0 &&
		  hessian_map[ptr_to_var2][ptr_to_var1]["obj"].size() == 0)
		{
		  hessian_map[ptr_to_var2].erase(ptr_to_var1);
		}
	      if (hessian_map[ptr_to_var2].size() == 0)
		{
		  hessian_map.erase(ptr_to_var2);
		}
	    }
	  ++var_iter2;
	}
      ++var_iter1;
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
