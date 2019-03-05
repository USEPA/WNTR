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


double evaluate(std::vector<int>* rpn, std::vector<double*>* values)
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
	  stack[stack_ndx] = *((*values)[ndx]);
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


void Evaluator::set_structure()
{
  fn_rpn.clear();
  fn_leaf_values.clear();
  jac_rpn.clear();
  jac_leaf_values.clear();
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

  std::set<Constraint*>::iterator con_iter;
  for (con_iter = con_set.begin(); con_iter != con_set.end(); ++con_iter)
    {
      fn_rpn.push_back((*con_iter)->fn_rpn);
      std::vector<double*> leaf_vals;
      
    }
}
