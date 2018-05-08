// To build wrapper:
//     swig -c++ -python -builtin aml_core.i
//     python setup.py build_ext --inplace

#include "aml_tnlp.hpp"

using namespace Ipopt;


AML_NLP::AML_NLP()
{}


AML_NLP::~AML_NLP()
{}


bool AML_NLP::get_nlp_info(Index &n, Index &m, Index &nnz_jac_g,
                           Index &nnz_h_lag, TNLP::IndexStyleEnum &index_style)
{
  n = (get_model()->vars).size();
  m = (get_model()->cons).size();
  nnz_jac_g = 0;
  for (auto &ptr_to_con : get_model()->cons)
    {
      nnz_jac_g += ptr_to_con->expr->get_vars()->size();
    }
  nnz_h_lag = 0;
  for (auto &row : get_model()->hessian_map)
    {
      for (auto &col : row.second)
        {
	  assert(col.second["cons"].size() > 0 || col.second["obj"].size() > 0);
	  nnz_h_lag += 1;
        }
    }
  index_style = TNLP::C_STYLE;
  
  return true;
}


bool AML_NLP::get_bounds_info(Index n, Number *x_l, Number *x_u,
                              Index m, Number *g_l, Number *g_u)
{
  int i = 0;
  for (auto &ptr_to_var : get_model()->vars)
    {
      x_l[i] = ptr_to_var->lb;
      x_u[i] = ptr_to_var->ub;
      ++i;
    }
  
  i = 0;
  for (auto &ptr_to_con : get_model()->cons)
    {
      g_l[i] = ptr_to_con->lb;
      g_u[i] = ptr_to_con->ub;
      ++i;
    }
  
  return true;
}


bool AML_NLP::get_starting_point(Index n, bool init_x, Number *x,
                                 bool init_z, Number *z_L, Number *z_U,
                                 Index m, bool init_lambda,
                                 Number *lambda)
{
  if (init_x)
    {
      int i = 0;
      for (auto &ptr_to_var : get_model()->vars)
        {
	  x[i] = ptr_to_var->value;
	  ++i;
        }
    }
  
  if (init_z)
    {
      int i = 0;
      for (auto &ptr_to_var : get_model()->vars)
        {
	  z_L[i] = ptr_to_var->lb_dual;
	  z_U[i] = ptr_to_var->ub_dual;
	  ++i;
        }
    }
  
  if (init_lambda)
    {
      int i = 0;
      for (auto &ptr_to_con : get_model()->cons)
        {
	  lambda[i] = ptr_to_con->dual;
	  ++i;
        }
    }
  
  return true;
}


bool AML_NLP::eval_f(Index n, const Number *x, bool new_x, Number &obj_value)
{
  if (new_x)
    {
      for (auto &ptr_to_var : get_model()->vars)
        {
	  ptr_to_var->value = x[ptr_to_var->index];
        }
      get_model()->obj->expr->evaluate();
      for (auto &ptr_to_con : get_model()->cons)
	{
	  ptr_to_con->expr->evaluate();
	}
    }
  
  obj_value = get_model()->obj->expr->value;
  
  return true;
}


bool AML_NLP::eval_grad_f(Index n, const Number *x, bool new_x, Number *grad_f)
{
  if (new_x)
    {
      for (auto &ptr_to_var : get_model()->vars)
        {
	  ptr_to_var->value = x[ptr_to_var->index];
        }
      get_model()->obj->expr->evaluate();
      for (auto &ptr_to_con : get_model()->cons)
	{
	  ptr_to_con->expr->evaluate();
	}
    }
  
  for (int i=0; i<n; ++i)
    {
      grad_f[i] = 0.0;
    }
  
  auto obj_vars = get_model()->obj->expr->get_vars();
  for (auto &ptr_to_var : *(obj_vars))
    {
      grad_f[ptr_to_var->index] = get_model()->obj->expr->ad(*ptr_to_var, false);
    }
  
  return true;
}


bool AML_NLP::eval_g(Index n, const Number *x, bool new_x, Index m, Number *g)
{
  if (new_x)
    {
      for (auto &ptr_to_var : get_model()->vars)
        {
	  ptr_to_var->value = x[ptr_to_var->index];
        }
      get_model()->obj->expr->evaluate();
      for (auto &ptr_to_con : get_model()->cons)
	{
	  ptr_to_con->expr->evaluate();
	}
    }
  
  int i = 0;
  for (auto &ptr_to_con : get_model()->cons)
    {
      g[i] = ptr_to_con->expr->value;
      ++i;
    }
  
  return true;
}


bool AML_NLP::eval_jac_g(Index n, const Number *x, bool new_x,
                         Index m, Index nele_jac, Index *iRow, Index *jCol,
                         Number *values)
{
  if (values == NULL)
    {
      int i = 0;
      std::shared_ptr<std::set<std::shared_ptr<Var> > > con_vars;
      for (auto &ptr_to_con : get_model()->cons)
        {
	  con_vars = ptr_to_con->expr->get_vars();
	  for (auto &ptr_to_var : (*con_vars))
            {
	      iRow[i] = ptr_to_con->index;
	      jCol[i] = ptr_to_var->index;
	      ++i;
            }
        }
    }
  else
    {
      if (new_x)
        {
	  for (auto &ptr_to_var : get_model()->vars)
            {
	      ptr_to_var->value = x[ptr_to_var->index];
            }
	  get_model()->obj->expr->evaluate();
	  for (auto &ptr_to_con : get_model()->cons)
	    {
	      ptr_to_con->expr->evaluate();
	    }
        }
      int i = 0;
      std::shared_ptr<std::set<std::shared_ptr<Var> > > con_vars;
      for (auto &ptr_to_con : get_model()->cons)
        {
	  con_vars = ptr_to_con->expr->get_vars();
	  for (auto &ptr_to_var : (*con_vars))
            {
	      values[i] = ptr_to_con->expr->ad(*ptr_to_var, false);
	      ++i;
            }
        }
    }
  
  return true;
}


bool AML_NLP::eval_h(Index n, const Number *x, bool new_x,
                     Number obj_factor, Index m, const Number *lambda,
                     bool new_lambda, Index nele_hess, Index *iRow,
                     Index *jCol, Number *values)
{
  if (values == NULL)
    {
      int i = 0;
      for (auto &row : get_model()->hessian_map)
        {
	  for (auto &col : row.second)
            {
	      iRow[i] = row.first->index;
	      jCol[i] = col.first->index;
	      ++i;
            }
        }
    }
  else
    {
      if (new_x)
        {
	  for (auto &ptr_to_var : get_model()->vars)
            {
	      ptr_to_var->value = x[ptr_to_var->index];
            }
	  get_model()->obj->expr->evaluate();
	  for (auto &ptr_to_con : get_model()->cons)
	    {
	      ptr_to_con->expr->evaluate();
	    }
        }
      if (new_lambda)
        {
	  for (auto &ptr_to_con : get_model()->cons)
            {
	      ptr_to_con->dual = lambda[ptr_to_con->index];
            }
        }
      int i = 0;
      for (auto &row : get_model()->hessian_map)
        {
	  for (auto &col : row.second)
            {
	      values[i] = 0;
	      for (auto &ptr_to_obj : col.second["obj"])
                {
		  values[i] += obj_factor * ptr_to_obj->expr->ad2(*row.first, *col.first, false);
                }
	      for (auto &ptr_to_con : col.second["cons"])
                {
		  values[i] += lambda[ptr_to_con->index] * ptr_to_con->expr->ad2(*row.first, *col.first, false);
                }
	      ++i;
            }
        }
    }
  
  return true;
}


void AML_NLP::finalize_solution(SolverReturn status, Index n, const Number *x, const Number *z_L, const Number *z_U,
                                Index m, const Number *g, const Number *lambda, Number obj_value,
                                const IpoptData *ip_data, IpoptCalculatedQuantities *ip_cq)
{
  if (status == SUCCESS)
    {
      get_model()->solver_status = "SUCCESS";
    }
  else if (status == MAXITER_EXCEEDED)
    {
      get_model()->solver_status = "MAXITER_EXCEEDED";
    }
  else if (status == CPUTIME_EXCEEDED)
    {
      get_model()->solver_status = "CPUTIME_EXCEEDED";
    }
  else if (status == STOP_AT_TINY_STEP)
    {
      get_model()->solver_status = "STOP_AT_TINY_STEP";
    }
  else if (status == STOP_AT_ACCEPTABLE_POINT)
    {
      get_model()->solver_status = "STOP_AT_ACCEPTABLE_POINT";
    }
  else if (status == LOCAL_INFEASIBILITY)
    {
      get_model()->solver_status = "LOCAL_INFEASIBILITY";
    }
  else if (status == USER_REQUESTED_STOP)
    {
      get_model()->solver_status = "USER_REQUESTED_STOP";
    }
  else if (status == DIVERGING_ITERATES)
    {
      get_model()->solver_status = "DIVERGING_ITERATES";
    }
  else if (status == RESTORATION_FAILURE)
    {
      get_model()->solver_status = "RESTORATION_FAILURE";
    }
  else if (status == ERROR_IN_STEP_COMPUTATION)
    {
      get_model()->solver_status = "ERROR_IN_STEP_COMPUTATION";
    }
  else if (status == INVALID_NUMBER_DETECTED)
    {
      get_model()->solver_status = "INVALID_NUMBER_DETECTED";
    }
  else if (status == INTERNAL_ERROR)
    {
      get_model()->solver_status = "INTERNAL_ERROR";
    }
  else
    {
      get_model()->solver_status = "UNKNOWN";
    }
  
  for (auto &ptr_to_var : get_model()->vars)
    {
      ptr_to_var->value = x[ptr_to_var->index];
      ptr_to_var->lb_dual = z_L[ptr_to_var->index];
      ptr_to_var->ub_dual = z_U[ptr_to_var->index];
    }
  
  for (auto &ptr_to_con : get_model()->cons)
    {
      ptr_to_con->dual = lambda[ptr_to_con->index];
    }
}


IpoptModel* AML_NLP::get_model()
{
  return model;
}


void AML_NLP::set_model(IpoptModel *m)
{
  model = m;
}
