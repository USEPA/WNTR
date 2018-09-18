#include "expression.hpp"


int ADD = -1;
int SUBTRACT = -2;
int MULTIPLY = -3;
int DIVIDE = -4;
int POWER = -5;


template<int N_LEAVES, int RPN_LENGTH>
class QuickExpr
{
public:
  int rpn[RPN_LENGTH];
  int rpn_length = RPN_LENGTH;
  double *leaf_vals[N_LEAVES];
  double stack[RPN_LENGTH];
  double evaluate();
}
