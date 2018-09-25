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
  ~Evaluator();
  
  double evaluate();
  //void rad();
};
