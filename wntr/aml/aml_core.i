%module aml_core
%include <std_shared_ptr.i>
%shared_ptr(Var)
%shared_ptr(Param)
%shared_ptr(Float)
%shared_ptr(Expression)
%shared_ptr(AddOperator)
%shared_ptr(SubtractOperator)
%shared_ptr(MultiplyOperator)
%shared_ptr(DivideOperator)
%shared_ptr(PowerOperator)
%shared_ptr(Node)
%shared_ptr(ExpressionBase)
%shared_ptr(Leaf)
%shared_ptr(Operator)
%shared_ptr(BinaryOperator)
%feature("kwargs");
%feature("autodoc","3");
%{
  #define SWIG_FILE_WITH_INIT
  #include "expression.hpp"
%}

%include "std_string.i"
%include "pyabc.i"

%include "expression.hpp"
