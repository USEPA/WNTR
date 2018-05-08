%module expression
%include <std_shared_ptr.i>
%shared_ptr(Var)
%shared_ptr(Param)
%shared_ptr(Expression)
%shared_ptr(Summation)
%shared_ptr(VarVarMultiplyOperator)
%shared_ptr(VarParamMultiplyOperator)
%shared_ptr(VarOperatorMultiplyOperator)
%shared_ptr(ParamVarMultiplyOperator)
%shared_ptr(ParamParamMultiplyOperator)
%shared_ptr(ParamOperatorMultiplyOperator)
%shared_ptr(OperatorVarMultiplyOperator)
%shared_ptr(OperatorParamMultiplyOperator)
%shared_ptr(OperatorOperatorMultiplyOperator)
%shared_ptr(VarVarDivideOperator)
%shared_ptr(VarParamDivideOperator)
%shared_ptr(VarOperatorDivideOperator)
%shared_ptr(ParamVarDivideOperator)
%shared_ptr(ParamParamDivideOperator)
%shared_ptr(ParamOperatorDivideOperator)
%shared_ptr(OperatorVarDivideOperator)
%shared_ptr(OperatorParamDivideOperator)
%shared_ptr(OperatorOperatorDivideOperator)
%shared_ptr(VarVarPowerOperator)
%shared_ptr(VarParamPowerOperator)
%shared_ptr(VarOperatorPowerOperator)
%shared_ptr(ParamVarPowerOperator)
%shared_ptr(ParamParamPowerOperator)
%shared_ptr(ParamOperatorPowerOperator)
%shared_ptr(OperatorVarPowerOperator)
%shared_ptr(OperatorParamPowerOperator)
%shared_ptr(OperatorOperatorPowerOperator)
%shared_ptr(Node)
%{
  #include "expression.hpp"
%}

%include "std_string.i"
%include "expression.hpp"
