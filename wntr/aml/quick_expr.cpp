#include "quick_expr.hpp"

double QuickExpr::evaluate()
{
  int stack_ndx = 0;
  int ndx;
  double v1;
  double v2;
  for (int i=0; i < rpn_length; ++i)
    {
      ndx = rpn[i];
      if (ndx >= 0)
	{
	  stack[stack_ndx] = *(leaf_vals[ndx]);
	  stack_ndx += 1;
	}
      else
	{
	  if (ndx == ADD)
	    {
	      v1 = stack[stack_ndx - 2];
	      v2 = stack[stack_ndx - 1];
	      stack[stack_ndx - 2] = v1 + v2;
	      stack_ndx -= 1;
	    }
	  else if (ndx == SUBTRACT)
	    {
	      v1 = stack[stack_ndx - 2];
	      v2 = stack[stack_ndx - 1];
	      stack[stack_ndx - 2] = v1 - v2;
	      stack_ndx -= 1;
	    }
	  else if (ndx == MULTIPLY)
	    {
	      v1 = stack[stack_ndx - 2];
	      v2 = stack[stack_ndx - 1];
	      stack[stack_ndx - 2] = v1 * v2;
	      stack_ndx -= 1;
	    }
	  else if (ndx == DIVIDE)
	    {
	      v1 = stack[stack_ndx - 2];
	      v2 = stack[stack_ndx - 1];
	      stack[stack_ndx - 2] = v1 / v2;
	      stack_ndx -= 1;
	    }
	  else if (ndx == POWER)
	    {
	      v1 = stack[stack_ndx - 2];
	      v2 = stack[stack_ndx - 1];
	      stack[stack_ndx - 2] = std::pow(v1,v2);
	      stack_ndx -= 1;
	    }
	}
    }
  return stack[stack_ndx - 1];
}
