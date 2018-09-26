%module aml_core
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
%template(var_vector) std::vector<Var*>;
%newobject ExpressionBase::operator+(ExpressionBase&);
%newobject ExpressionBase::operator-(ExpressionBase&);
%newobject ExpressionBase::operator*(ExpressionBase&);
%newobject ExpressionBase::operator/(ExpressionBase&);
%newobject ExpressionBase::__pow__(ExpressionBase&);
%newobject ExpressionBase::operator-();
%newobject ExpressionBase::operator+(double);
%newobject ExpressionBase::operator-(double);
%newobject ExpressionBase::operator*(double);
%newobject ExpressionBase::operator/(double);
%newobject ExpressionBase::__pow__(double);
%newobject ExpressionBase::__radd__(double);
%newobject ExpressionBase::__rsub__(double);
%newobject ExpressionBase::__rmul__(double);
%newobject ExpressionBase::__rdiv__(double);
%newobject ExpressionBase::__rtruediv__(double);
%newobject ExpressionBase::__rpow__(double);

%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *array_out, int array_length_out)}
%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *values_array_out, int values_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *col_ndx_array_out, int col_ndx_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *row_nnz_array_out, int row_nnz_array_length_out)}
%apply (double *IN_ARRAY1, int DIM1) {(double *array_in, int array_length_in)}

%include "expression.hpp"
%include "evaluator.hpp"
%include "component.hpp"
%include "wntr_model.hpp"
