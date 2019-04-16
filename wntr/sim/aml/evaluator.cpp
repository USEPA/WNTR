#include "evaluator.hpp"


void Constraint::add_leaf(Leaf* leaf)
{
  leaves.push_back(leaf);
}


void Constraint::add_fn_rpn_term(int term)
{
  fn_rpn.push_back(term);
}


void Constraint::add_jac_rpn_term(Var* v, int term)
{
  jac_rpn[v].push_back(term);
}


void IfElseConstraint::add_leaf(Leaf* leaf)
{
  leaves.push_back(leaf);
}


void IfElseConstraint::end_condition()
{
  condition_rpn.push_back(current_condition_rpn);
  fn_rpn.push_back(current_fn_rpn);

  std::map<Var*, std::vector<int> >::iterator jac_rpn_iter;
  for (jac_rpn_iter=current_jac_rpn.begin(); jac_rpn_iter!=current_jac_rpn.end(); ++jac_rpn_iter)
    {
      jac_rpn[jac_rpn_iter->first].push_back(jac_rpn_iter->second);
    }
  
  current_condition_rpn.clear();
  current_fn_rpn.clear();
  current_jac_rpn.clear();
}


void IfElseConstraint::add_condition_rpn_term(int term)
{
  current_condition_rpn.push_back(term);
}


void IfElseConstraint::add_fn_rpn_term(int term)
{
  current_fn_rpn.push_back(term);
}


void IfElseConstraint::add_jac_rpn_term(Var* v, int term)
{
  current_jac_rpn[v].push_back(term);
}


double _evaluate(double* stack, std::vector<int>* rpn, std::vector<Leaf*>* values)
{
  double arg1;
  double arg2;
  double arg;
  double res;
  int stack_ndx = 0;
  int rpn_size = rpn->size();
  int ndx;
  for (int i=0; i<rpn_size; ++i)
    {
      ndx = (*rpn)[i];
      if (ndx >= 0)
	{
	  stack[stack_ndx] = ((*values)[ndx])->value;
	  ++stack_ndx;
	}
      else
	{
	  if (ndx == ADD)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      res = arg1 + arg2;
	    }
	  else if (ndx == SUB)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      res = arg1 - arg2;
	    }
	  else if (ndx == MUL)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      res = arg1 * arg2;
	    }
	  else if (ndx == DIV)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      res = arg1 / arg2;
	    }
	  else if (ndx == POW)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      res = ::pow(arg1, arg2);
	    }
	  else if (ndx == ABS)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = std::abs(arg);
	    }
	  else if (ndx == SIGN)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      if (arg >= 0)
		res = 1.0;
	      else
		res = -1.0;
	    }
	  else if (ndx == IF_ELSE)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      if (arg == 1)
		{
		  res = arg1;
		}
	      else
		{
		  res = arg2;
		}
	    }
	  else if (ndx == INEQUALITY)
	    {
	      --stack_ndx;
	      arg2 = stack[stack_ndx];
	      --stack_ndx;
	      arg1 = stack[stack_ndx];
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      if (arg >= arg1 && arg <= arg2)
		res = 1.0;
	      else
		res = 0.0;
	    }
	  else if (ndx == EXP)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::exp(arg);
	    }
	  else if (ndx == LOG)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::log(arg);
	    }
	  else if (ndx == NEGATION)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = -arg;
	    }
	  else if (ndx == SIN)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::sin(arg);
	    }
	  else if (ndx == COS)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::cos(arg);
	    }
	  else if (ndx == TAN)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::tan(arg);
	    }
	  else if (ndx == ASIN)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::asin(arg);
	    }
	  else if (ndx == ACOS)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::acos(arg);
	    }
	  else if (ndx == ATAN)
	    {
	      --stack_ndx;
	      arg = stack[stack_ndx];
	      res = ::atan(arg);
	    }
	  else
	    throw std::runtime_error("Operation not recognized");
	  stack[stack_ndx] = res;
	  ++stack_ndx;
	}
    }
  --stack_ndx;
  res = stack[stack_ndx];
  return res;
}


Evaluator::~Evaluator()
{
  if (is_structure_set)
    {
      remove_structure();
    }
  
  std::set<Constraint*>::iterator con_iter;
  for (con_iter = con_set.begin(); con_iter != con_set.end(); ++con_iter)
    {
      delete (*con_iter);
    }

  std::set<IfElseConstraint*>::iterator if_else_con_iter;
  for (if_else_con_iter = if_else_con_set.begin(); if_else_con_iter != if_else_con_set.end(); ++if_else_con_iter)
    {
      delete (*if_else_con_iter);
    }

  std::set<Var*>::iterator var_iter;
  for (var_iter = var_set.begin(); var_iter != var_set.end(); ++var_iter)
    {
      delete (*var_iter);
    }

  std::set<Param*>::iterator param_iter;
  for (param_iter = param_set.begin(); param_iter != param_set.end(); ++param_iter)
    {
      delete (*param_iter);
    }

  std::set<Float*>::iterator float_iter;
  for (float_iter = float_set.begin(); float_iter != float_set.end(); ++float_iter)
    {
      delete (*float_iter);
    }
}


Var* Evaluator::add_var(double value)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  Var* v = new Var(value);
  var_set.insert(v);
  return v;
}


Param* Evaluator::add_param(double value)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  Param* p = new Param(value);
  param_set.insert(p);
  return p;
}


Float* Evaluator::add_float(double value)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  Float* f = new Float(value);
  float_set.insert(f);
  return f;
}


Constraint* Evaluator::add_constraint()
{
  if (is_structure_set)
    {
      remove_structure();
    }
  Constraint* c = new Constraint();
  con_set.insert(c);
  return c;
}


IfElseConstraint* Evaluator::add_if_else_constraint()
{
  if (is_structure_set)
    {
      remove_structure();
    }
  IfElseConstraint* c = new IfElseConstraint();
  if_else_con_set.insert(c);
  return c;
}


void Evaluator::remove_var(Var* v)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  var_set.erase(v);
  delete v;
}


void Evaluator::remove_param(Param* p)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  param_set.erase(p);
  delete p;
}


void Evaluator::remove_float(Float* f)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  float_set.erase(f);
  delete f;
}


void Evaluator::remove_constraint(Constraint* c)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  con_set.erase(c);
  delete c;
}


void Evaluator::remove_if_else_constraint(IfElseConstraint* c)
{
  if (is_structure_set)
    {
      remove_structure();
    }
  if_else_con_set.erase(c);
  delete c;
}


void Evaluator::set_structure()
{
  if (is_structure_set)
    {
      remove_structure();
    }
  is_structure_set = true;
  var_vector.clear();
  leaves.clear();
  col_ndx.clear();
  row_nnz.clear();

  fn_rpn.clear();
  jac_rpn.clear();

  n_conditions.clear();
  if_else_condition_rpn.clear();
  if_else_fn_rpn.clear();
  if_else_jac_rpn.clear();

  int max_rpn_size = 0;

  //******************************************
  // Variables
  //******************************************
  std::set<Var*>::iterator var_iter;
  int ndx = 0;
  for (var_iter = var_set.begin(); var_iter != var_set.end(); ++var_iter)
    {
      var_vector.push_back(*var_iter);
      (*var_iter)->index = ndx;
      ++ndx;
    }

  //******************************************
  // Constraints
  //******************************************
  row_nnz.push_back(0);
  ndx = 0;
  std::set<Constraint*>::iterator con_iter;
  for (con_iter = con_set.begin(); con_iter != con_set.end(); ++con_iter)
    {
      Constraint* con = *con_iter;
      con->index = ndx;
      leaves.push_back(con->leaves);
      fn_rpn.push_back(con->fn_rpn);
      if (con->fn_rpn.size() > max_rpn_size)
	max_rpn_size = con->fn_rpn.size();
      row_nnz.push_back(row_nnz[ndx] + con->jac_rpn.size());
      std::map<Var*, std::vector<int> >::iterator jac_rpn_iter;
      for (jac_rpn_iter = con->jac_rpn.begin(); jac_rpn_iter != con->jac_rpn.end(); ++jac_rpn_iter)
	{
	  col_ndx.push_back(jac_rpn_iter->first->index);
	  jac_rpn.push_back(jac_rpn_iter->second);
	  if (jac_rpn_iter->second.size() > max_rpn_size)
	    max_rpn_size = jac_rpn_iter->second.size();
	}
      ++ndx;
    }

  //******************************************
  // IfElseConstraints
  //******************************************
  std::set<IfElseConstraint*>::iterator if_else_con_iter;
  int _n_conditions = 0;
  for (if_else_con_iter = if_else_con_set.begin(); if_else_con_iter != if_else_con_set.end(); ++if_else_con_iter)
    {
      IfElseConstraint* con = *if_else_con_iter;
      con->index = ndx;
      leaves.push_back(con->leaves);
      _n_conditions = con->condition_rpn.size();
      n_conditions.push_back(_n_conditions);
      row_nnz.push_back(row_nnz[ndx] + con->jac_rpn.size()); // every vector in con->jac_rpn should be the same size
      for (int i=0; i<_n_conditions; ++i)
	{
	  if_else_condition_rpn.push_back(con->condition_rpn[i]);
	  if (con->condition_rpn[i].size() > max_rpn_size)
	    max_rpn_size = con->condition_rpn[i].size();
	  if_else_fn_rpn.push_back(con->fn_rpn[i]);
	  if (con->fn_rpn[i].size() > max_rpn_size)
	    max_rpn_size = con->fn_rpn[i].size();
	  for (std::map<Var*, std::vector<std::vector<int> > >::iterator jac_rpn_iter=con->jac_rpn.begin(); jac_rpn_iter!=con->jac_rpn.end(); ++jac_rpn_iter)
	    {
	      if (((int) jac_rpn_iter->second.size()) != _n_conditions)
		{
		  throw StructureException("The number of vectors in jac_rpn must be equal to the number of conditions for an IfElseConstraint.");
		}
	      if (i==0)
		{
		  col_ndx.push_back(jac_rpn_iter->first->index);
		}
	      if_else_jac_rpn.push_back(jac_rpn_iter->second[i]);
	      if (jac_rpn_iter->second[i].size() > max_rpn_size)
		max_rpn_size = jac_rpn_iter->second[i].size();
	    }
	}
      ++ndx;
    }
  
  nnz = row_nnz.back();
  stack = new double[max_rpn_size];
}


void Evaluator::remove_structure()
{
  if (is_structure_set)
    {
      is_structure_set = false;
      delete[] stack;
    }
}


void Evaluator::evaluate(double* array_out, int array_length_out)
{
  if (!is_structure_set)
    {
      throw StructureException("Cannot call evaluate() if the structure is not set. Please call set_structure() first.");
    }
  int num_cons = con_set.size();
  int num_if_else_cons = if_else_con_set.size();
  int con_ndx = 0;
  while (con_ndx<num_cons)
    {
      array_out[con_ndx] = _evaluate(stack, &(fn_rpn[con_ndx]), &(leaves[con_ndx]));
      ++con_ndx;
    }

  int c = 0;
  int _n_conditions = 0;
  bool found;
  int condition_ndx = 0;
  int i;
  while (con_ndx < num_cons + num_if_else_cons)
    {
      found = false;
      _n_conditions = n_conditions[c];
      i = 0;
      while (!found)
	{
	  if (if_else_condition_rpn[condition_ndx].size() == 0)
	    {
	      found = true;
	    }
	  else if (_evaluate(stack, &(if_else_condition_rpn[condition_ndx]), &(leaves[con_ndx])) == 1)
	    {
	      found = true;
	    }

	  if (found)
	    {
	      array_out[con_ndx] = _evaluate(stack, &(if_else_fn_rpn[condition_ndx]), &(leaves[con_ndx]));
	      condition_ndx += _n_conditions - i;
	    }
	  else
	    {
	      ++condition_ndx;
	      ++i;
	    }
	}
      ++c;
      ++con_ndx;
    }
}


void Evaluator::evaluate_csr_jacobian(double* values_array_out, int values_array_length_out, int* col_ndx_array_out, int col_ndx_array_length_out, int* row_nnz_array_out, int row_nnz_array_length_out)
{
  if (!is_structure_set)
    {
      throw StructureException("Cannot call evaluate_csr_jacobian() if the structure is not set. Please call set_structure() first.");
    }
  int num_cons = con_set.size();
  int num_if_else_cons = if_else_con_set.size();
  row_nnz_array_out[0] = 0;
  int nnz_ndx = 0;
  int nnz;

  int con_ndx = 0;
  while (con_ndx < num_cons)
    {
      row_nnz_array_out[con_ndx+1] = row_nnz[con_ndx+1];
      nnz = row_nnz[con_ndx+1] - row_nnz[con_ndx];
      for (int i=0; i<nnz; ++i)
	{
	  values_array_out[nnz_ndx] = _evaluate(stack, &(jac_rpn[nnz_ndx]), &(leaves[con_ndx]));
	  col_ndx_array_out[nnz_ndx] = col_ndx[nnz_ndx];
	  ++nnz_ndx;
	}
      ++con_ndx;
    }

  int c = 0;
  int i = 0;
  int _n_conditions = 0;
  bool found;
  int condition_ndx = 0;
  int jac_ndx = 0;
  while (con_ndx < num_cons + num_if_else_cons)
    {
      row_nnz_array_out[con_ndx+1] = row_nnz[con_ndx+1];
      nnz = row_nnz[con_ndx+1] - row_nnz[con_ndx];
      _n_conditions = n_conditions[c];
      i = 0;
      found = false;
      while (!found)
	{
	  if (if_else_condition_rpn[condition_ndx].size() == 0)
	    {
	      found = true;
	    }
	  else if (_evaluate(stack, &(if_else_condition_rpn[condition_ndx]), &(leaves[con_ndx])) == 1)
	    {
	      found = true;
	    }

	  if (found)
	    {
	      for (int j=0; j<nnz; ++j)
		{
		  values_array_out[nnz_ndx] = _evaluate(stack, &(if_else_jac_rpn[jac_ndx]), &(leaves[con_ndx]));
		  col_ndx_array_out[nnz_ndx] = col_ndx[nnz_ndx];
		  ++nnz_ndx;
		  ++jac_ndx;
		}
	      condition_ndx += _n_conditions - i;
	      jac_ndx += (_n_conditions - i - 1) * nnz;
	    }
	  else
	    {
	      ++condition_ndx;
	      ++i;
	      jac_ndx += nnz;
	    }
	}
      ++con_ndx;
      ++c;
    }
}


void Evaluator::get_x(double *array_out, int array_length_out)
{
  if (!is_structure_set)
    {
      throw StructureException("Cannot call get_x() if the structure is not set. Please call set_structure() first.");
    }
  int n_vars = var_vector.size();
  for (int i=0; i<n_vars; ++i)
    {
      array_out[i] = var_vector[i]->value;
    }
}


void Evaluator::load_var_values_from_x(double *arrayin, int array_length_in)
{
  if (!is_structure_set)
    {
      throw StructureException("Cannot call load_var_values_from_x() if the structure is not set. Please call set_structure() first.");
    }
  int n_vars = var_vector.size();
  for (int i=0; i<n_vars; ++i)
    {
      var_vector[i]->value = arrayin[i];
    }
}


