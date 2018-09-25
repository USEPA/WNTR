#include "evaluator.hpp"


Evaluator::Evaluator(ExpressionBase* expr)
{
  if (expr->is_leaf())
    {
      Leaf* leaf = dynamic_cast<Leaf*>(expr);
      n_operators = 1;
      n_leaves = 1;
      operators = new short[n_operators];
      arg1_indices = new int[n_operators];
      arg2_indices = new int[n_operators];
      leaves = new Leaf*[1];
      operators[0] = VALUE;
      arg1_indices[0] = 0;
      arg2_indices[0] = 0;
      leaves[0] = leaf;
    }
  else
    {
      Expression* _expr = dynamic_cast<Expression*>(expr);
      n_operators = _expr->num_operators;
      n_leaves = _expr->num_leaves;
      operators = new short[n_operators];
      arg1_indices = new int[n_operators];
      arg2_indices = new int[n_operators];
      leaves = new Leaf*[_expr->num_leaves];

      for (int i=0; i<n_operators; ++i)
	{
	  operators[i] = (*(_expr->operators))[i];
	  arg1_indices[i] = (*(_expr->args1))[i];
	  arg2_indices[i] = (*(_expr->args2))[i];
	}

      Leaf *leaf;
      for (int i=0; i<_expr->num_leaves; ++i)
	{
	  leaf = (*(_expr->leaves))[i];
	  leaves[i] = leaf;
	  if (leaf->is_float())
	    {
	      Float *f = dynamic_cast<Float*>(leaf);
	      f->refcount += 1;
	    }
	}
    }
}


Evaluator::~Evaluator()
{
  Leaf *leaf;
  Float *f;
  for (int i=0; i<n_leaves; ++i)
    {
      leaf = leaves[i];
      if (leaf->is_float())
	{
	  f = dynamic_cast<Float*>(leaf);
	  f->refcount -= 1;
	  if (f->refcount == 0)
	    {
	      delete f;
	    }
	}
    }
  delete operators;
  delete arg1_indices;
  delete arg2_indices;
  delete leaves;
}


double Evaluator::evaluate()
{
  short oper;
  int arg1_ndx;
  int arg2_ndx;
  double val1;
  double val2;
  double values[n_operators];
  int oper_ndx;
  
  for (int i=0; i<n_operators; ++i)
    {
      oper = operators[i];
      arg1_ndx = arg1_indices[i];
      arg2_ndx = arg2_indices[i];
      if (arg1_ndx >= 0)
	{
	  val1 = leaves[arg1_ndx]->value;
	}
      else
	{
	  oper_ndx = _arg_ndx_to_operator_ndx(arg1_ndx);
	  val1 = values[oper_ndx];
	}
      if (arg2_ndx >= 0)
	{
	  val2 = leaves[arg2_ndx]->value;
	}
      else
	{
	  oper_ndx = _arg_ndx_to_operator_ndx(arg2_ndx);
	  val2 = values[oper_ndx];
	}
      
      if (oper == ADD)
	{
	  values[i] = val1 + val2;
	}
      else if (oper == VALUE)
	{
	  values[i] = val1;
	}
      else if (oper == SUBTRACT)
	{
	  values[i] = val1 - val2;
	}
      else if (oper == MULTIPLY)
	{
	  values[i] = val1 * val2;
	}
      else if (oper == DIVIDE)
	{
	  values[i] = val1 / val2;
	}
      else if (oper == POWER)
	{
	  values[i] = ::pow(val1, val2);
	}
    }
  
  return values[n_operators - 1];
}


//void Evaluator::rad(bool new_eval)
//{
//  if (n_operators == 0)
//    {
//      assert (n_leaves == 1);
//      *(der_values[0]) = 1.0;
//    }
//  else
//    {
//      if (new_eval)
//	{
//	  evaluate();
//	}
//      
//      for (int i=0; i<n_operators+n_leaves; ++i)
//	{
//	  *(der_values[i]) = 0.0;
//	}
//      *(der_values[operator_indices[n_operators-1]]) = 1.0;
//      
//      int oper;
//      int oper_ndx;
//      int arg1_ndx;
//      int arg2_ndx;
//      double oper_der_value;
//      double arg1_value;
//      double arg2_value;
//      for (int i=n_operators-1; i>=0; --i)
//	{
//	  oper = operators[i];
//	  oper_ndx = operator_indices[i];
//	  arg1_ndx = arg1_indices[i];
//	  arg2_ndx = arg2_indices[i];
//	  oper_der_value = *(der_values[oper_ndx]);
//	  
//	  if (oper == ADD)
//	    {
//	      *(der_values[arg1_ndx]) += oper_der_value;
//	      *(der_values[arg2_ndx]) += oper_der_value;
//	    }
//	  else if (oper == SUBTRACT)
//	    {
//	      *(der_values[arg1_ndx]) += oper_der_value;
//	      *(der_values[arg2_ndx]) -= oper_der_value;
//	    }
//	  else if (oper == MULTIPLY)
//	    {
//	      *(der_values[arg1_ndx]) += oper_der_value * *(values[arg2_ndx]);
//	      *(der_values[arg2_ndx]) += oper_der_value * *(values[arg1_ndx]);
//	    }
//	  else if (oper == DIVIDE)
//	    {
//	      arg2_value = *(values[arg2_ndx]);
//	      *(der_values[arg1_ndx]) += oper_der_value / *(values[arg2_ndx]);
//	      *(der_values[arg2_ndx]) -= oper_der_value * *(values[arg1_ndx]) / (arg2_value * arg2_value);
//	    }
//	  else if (oper == POWER)
//	    {
//	      arg1_value = *(values[arg1_ndx]);
//	      arg2_value = *(values[arg2_ndx]);
//	      *(der_values[arg1_ndx]) += oper_der_value * arg2_value * ::pow(arg1_value, arg2_value - 1.0);
//	      *(der_values[arg2_ndx]) += oper_der_value * ::pow(arg1_value, arg2_value) * log(arg1_value);
//	    }
//	  else
//	    {
//	      throw std::runtime_error("unrecognized operator");
//	    }
//	}
//    }
//} 
