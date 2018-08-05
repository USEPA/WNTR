%module aml_core
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
%shared_ptr(Constraint)
%shared_ptr(ConditionalConstraint)
%shared_ptr(ConstraintBase)
%shared_ptr(Objective)
%shared_ptr(Component)
%shared_ptr(var_set)
%feature("kwargs");
%feature("autodoc","3");
%{
  #define SWIG_FILE_WITH_INIT
  #include "wntr_model.hpp"
%}

%include "numpy.i"
%init %{
  import_array();
%}
%include "std_string.i"
%include "pyabc.i"
%include "std_vector.i"
%include "std_set.i"
%include "std_list.i"
%template(double_vector) std::vector<double>;
%template(constraint_list) std::list<std::shared_ptr<ConstraintBase> >;
%template(var_list) std::list<std::shared_ptr<Var> >;
%template(var_set) std::set<std::shared_ptr<Var> >;
%template(int_list) std::list<int>;
%template(var_vec) std::vector<std::shared_ptr<Var> >;

%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *array_out, int array_length_out)}
%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *values_array_out, int values_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *col_ndx_array_out, int col_ndx_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *row_nnz_array_out, int row_nnz_array_length_out)}
%apply (double *IN_ARRAY1, int DIM1) {(double *array_in, int array_length_in)}

%include "expression.hpp"
%include "component.hpp"
%include "wntr_model.hpp"
