#include "evaluator.hpp"


double Evaluator::evaluate()
{
  if (n_operators == 0)
    {
      assert (n_leaves == 1);
      return *(values[0]);
    }

  int oper;
  int oper_ndx;
  int arg1_ndx;
  int arg2_ndx;
  for (int i=0; i<n_operators; ++i)
    {
      oper = operators[i];
      oper_ndx = operator_indices[i];
      arg1_ndx = arg1_indices[i];
      arg2_ndx = arg2_indices[i];

      if (oper == ADD)
	{
	  (*(values[oper_ndx])) = (*(values[arg1_ndx])) + (*(values[arg2_ndx]));
	}
      else if (oper == SUBTRACT)
	{
	  (*(values[oper_ndx])) = (*(values[arg1_ndx])) - (*(values[arg2_ndx]));
	}
      else if (oper == MULTIPLY)
	{
	  (*(values[oper_ndx])) = (*(values[arg1_ndx])) * (*(values[arg2_ndx]));
	}
      else if (oper == DIVIDE)
	{
	  (*(values[oper_ndx])) = (*(values[arg1_ndx])) / (*(values[arg2_ndx]));
	}
      else if (oper == POWER)
	{
	  (*(values[oper_ndx])) = ::pow((*(values[arg1_ndx])), (*(values[arg2_ndx])));
	}
      else
	{
	  throw std::runtime_error("unrecognized operator");
	}
    }
  return *(values[operator_indices[n_operators-1]]);
}


void Evaluator::rad(bool new_eval)
{
  if (n_operators == 0)
    {
      assert (n_leaves == 1);
      *(der_values[0]) = 1.0;
    }
  else
    {
      if (new_eval)
	{
	  evaluate();
	}
      
      for (int i=0; i<n_operators+n_leaves; ++i)
	{
	  *(der_values[i]) = 0.0;
	}
      *(der_values[operator_indices[n_operators-1]]) = 1.0;
      
      int oper;
      int oper_ndx;
      int arg1_ndx;
      int arg2_ndx;
      double oper_der_value;
      double arg1_value;
      double arg2_value;
      for (int i=n_operators-1; i>=0; --i)
	{
	  oper = operators[i];
	  oper_ndx = operator_indices[i];
	  arg1_ndx = arg1_indices[i];
	  arg2_ndx = arg2_indices[i];
	  oper_der_value = *(der_values[oper_ndx]);
	  
	  if (oper == ADD)
	    {
	      *(der_values[arg1_ndx]) += oper_der_value;
	      *(der_values[arg2_ndx]) += oper_der_value;
	    }
	  else if (oper == SUBTRACT)
	    {
	      *(der_values[arg1_ndx]) += oper_der_value;
	      *(der_values[arg2_ndx]) -= oper_der_value;
	    }
	  else if (oper == MULTIPLY)
	    {
	      *(der_values[arg1_ndx]) += oper_der_value * *(values[arg2_ndx]);
	      *(der_values[arg2_ndx]) += oper_der_value * *(values[arg1_ndx]);
	    }
	  else if (oper == DIVIDE)
	    {
	      arg2_value = *(values[arg2_ndx]);
	      *(der_values[arg1_ndx]) += oper_der_value / *(values[arg2_ndx]);
	      *(der_values[arg2_ndx]) -= oper_der_value * *(values[arg1_ndx]) / (arg2_value * arg2_value);
	    }
	  else if (oper == POWER)
	    {
	      arg1_value = *(values[arg1_ndx]);
	      arg2_value = *(values[arg2_ndx]);
	      *(der_values[arg1_ndx]) += oper_der_value * arg2_value * ::pow(arg1_value, arg2_value - 1.0);
	      *(der_values[arg2_ndx]) += oper_der_value * ::pow(arg1_value, arg2_value) * log(arg1_value);
	    }
	  else
	    {
	      throw std::runtime_error("unrecognized operator");
	    }
	}
    }
}


std::shared_ptr<Evaluator> create_evaluator(std::shared_ptr<ExpressionBase> expr)
{
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > leaves = expr->get_leaves();
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > operators = expr->get_operators();
  int n_leaves = leaves->size();
  int n_operators = expr->get_num_operators();
  std::shared_ptr<Evaluator> evaluator = std::make_shared<Evaluator>(n_operators, n_leaves);
  int count = 0;
  std::shared_ptr<Operator> oper;
  std::unordered_map<std::shared_ptr<Node>, int> indices;

  for (auto &leaf : *leaves)
    {
      indices[leaf] = count;
      evaluator->values[count] = &(leaf->value);
      evaluator->der_values[count] = &(leaf->der);
      count += 1;
    }

  for (int i=0; i<n_operators; ++i)
    {
      oper = (*operators)[i];
      evaluator->operators[i] = oper->get_operator_type();
      evaluator->operator_indices[i] = count;
      evaluator->arg1_indices[i] = indices[oper->arg1];
      if (oper->is_binary())
	{
	  evaluator->arg2_indices[i] = indices[oper->arg2];
	}
      else if (oper->is_unary())
	{
	  evaluator->arg2_indices[i] = -1;
	}
      else
	{
	  throw std::runtime_error("Unrecognized operator type.");
	}
      indices[oper] = count;
      evaluator->values[count] = &(oper->value);
      evaluator->der_values[count] = &(oper->der);
      count += 1;
    }

  return evaluator;
}
