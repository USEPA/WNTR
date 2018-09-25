#include "expression.hpp"


class Evaluator
{
public:
  int n_operators;
  int n_leaves;
  short *operators;
  int *arg1_indices;
  int *arg2_indices;
  Leaf **leaves;

  Evaluator(ExpressionBase*);
  Evaluator(const Evaluator&) = delete;
  Evaluator &operator=(const Evaluator&) = delete;
  ~Evaluator();
  
  double evaluate();
  void _evaluate(double *values);
  std::shared_ptr<std::unordered_map<Leaf*, double> > rad();
  std::string __str__();
};
