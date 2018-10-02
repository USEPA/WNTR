#include "expression.hpp"


class Evaluator
{
public:
  int n_operators;
  int n_leaves;
  int n_floats;
  short *operators;
  int *arg1_indices;
  int *arg2_indices;
  Leaf **leaves;
  Float **floats;

  Evaluator(ExpressionBase*);
  Evaluator(const Evaluator&) = delete;
  Evaluator &operator=(const Evaluator&) = delete;
  ~Evaluator();
  
  double evaluate();
  void _evaluate(double *values);
  void rad();
  std::string __str__();
  std::shared_ptr<std::vector<Var*> > get_vars();
  int get_n_vars();
};
