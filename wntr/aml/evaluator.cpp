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


double _evaluate(std::vector<int>* rpn, std::vector<Leaf*>* values)
{
  double stack[rpn->size()];
  double arg1;
  double arg2;
  double res;
  int stack_ndx = 0;
  for (auto& ndx : (*rpn))
    {
      if (ndx >= 0)
	{
	  stack[stack_ndx] = ((*values)[ndx])->value;
	  ++stack_ndx;
	}
      else
	{
	  --stack_ndx;
	  arg2 = stack[stack_ndx];
	  --stack_ndx;
	  arg1 = stack[stack_ndx];

	  if (ndx == ADD)
	    res = arg1 + arg2;
	  else if (ndx == SUB)
	    res = arg1 - arg2;
	  else if (ndx == MUL)
	    res = arg1 * arg2;
	  else if (ndx == DIV)
	    res = arg1 / arg2;
	  else
	    throw std::runtime_error("Operation not recognized");
	  stack[stack_ndx] = res;
	  ++stack_ndx;
	}
    }
  --stack_ndx;
  return stack[stack_ndx];
}


Evaluator::~Evaluator()
{
  std::set<Constraint*>::iterator con_iter;
  for (con_iter = con_set.begin(); con_iter != con_set.end(); ++con_iter)
    {
      delete (*con_iter);
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
  Var* v = new Var(value);
  var_set.insert(v);
  return v;
}


Param* Evaluator::add_param(double value)
{
  Param* p = new Param(value);
  param_set.insert(p);
  return p;
}


Float* Evaluator::add_float(double value)
{
  Float* f = new Float(value);
  float_set.insert(f);
  return f;
}


void Evaluator::remove_var(Var* v)
{
  var_set.erase(v);
  delete v;
}


void Evaluator::remove_param(Param* p)
{
  param_set.erase(p);
  delete p;
}


void Evaluator::remove_float(Float* f)
{
  float_set.erase(f);
  delete f;
}


void Evaluator::remove_constraint(Constraint* c)
{
  con_set.erase(c);
  delete c;
}


Constraint* Evaluator::add_constraint()
{
  Constraint* c = new Constraint();
  con_set.insert(c);
  return c;
}


void Evaluator::set_structure()
{
  fn_rpn.clear();
  leaves.clear();
  jac_rpn.clear();
  col_ndx.clear();
  row_nnz.clear();
  var_vector.clear();

  std::map<Var*, int> var_indices;
  std::set<Var*>::iterator var_iter;
  int ndx = 0;
  for (var_iter = var_set.begin(); var_iter != var_set.end(); ++var_iter)
    {
      var_vector.push_back(*var_iter);
      var_indices[*var_iter] = ndx;
      ++ndx;
    }

  row_nnz.push_back(0);
  ndx = 0;
  std::set<Constraint*>::iterator con_iter;
  for (con_iter = con_set.begin(); con_iter != con_set.end(); ++con_iter)
    {
      Constraint* con = *con_iter;
      leaves.push_back(con->leaves);
      fn_rpn.push_back(con->fn_rpn);
      row_nnz.push_back(row_nnz[ndx] + con->jac_rpn.size());
      std::map<Var*, std::vector<int> >::iterator jac_rpn_iter;
      for (jac_rpn_iter = con->jac_rpn.begin(); jac_rpn_iter != con->jac_rpn.end(); ++jac_rpn_iter)
	{
	  col_ndx.push_back(var_indices[jac_rpn_iter->first]);
	  jac_rpn.push_back(jac_rpn_iter->second);
	}
      ++ndx;
    }
}


void Evaluator::evaluate(double* array_out, int array_length_out)
{
  int num_cons = fn_rpn.size();
  for (int i=0; i<num_cons; ++i)
    {
      array_out[i] = _evaluate(&(fn_rpn[i]), &(leaves[i]));
    }
}


void Evaluator::evaluate_csr_jacobian(double* values_array_out, int values_array_length_out, int* col_ndx_array_out, int col_ndx_array_length_out, int* row_nnz_array_out, int row_nnz_array_length_out)
{
  int num_cons = fn_rpn.size();
  row_nnz[0] = 0;
  int nnz_ndx = 0;
  int nnz;
  for (int con_ndx=0; con_ndx<num_cons; ++con_ndx)
    {
      row_nnz_array_out[con_ndx+1] = row_nnz[con_ndx+1];
      nnz = row_nnz[con_ndx+1] - row_nnz[con_ndx];
      for (int i=0; i<nnz; ++i)
	{
	  values_array_out[nnz_ndx] = _evaluate(&(jac_rpn[nnz_ndx]), &(leaves[con_ndx]));
	  col_ndx_array_out[nnz_ndx] = col_ndx[nnz_ndx];
	  ++nnz_ndx;
	}
    }
}
