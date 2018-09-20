#include "expression.hpp"


class Evaluator
{
public:
  int n_operators;
  int n_leaves;
  int *operators;
  int *operator_indices;
  int *arg1_indices;
  int *arg2_indices;
  double **values;
  double **der_values;

  Evaluator(int _n_operators, int _n_leaves): n_operators(_n_operators), n_leaves(_n_leaves), operators(new int[_n_operators]), operator_indices(new int[_n_operators]), arg1_indices(new int[_n_operators]), arg2_indices(new int[_n_operators]), values(new double*[_n_operators+_n_leaves]), der_values(new double*[_n_operators+_n_leaves]) {}
  
  double evaluate();
  void rad(bool new_eval=true);
};


std::shared_ptr<Evaluator> create_evaluator(std::shared_ptr<ExpressionBase>);
