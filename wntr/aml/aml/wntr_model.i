%module wntr_model
%{
  #define SWIG_FILE_WITH_INIT
  #include "aml_core.hpp"
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
%template(constraint_list) std::list<ConstraintBase*>;
%template(var_list) std::list<Var*>;
%template(var_set) std::set<Var*>;
%template(int_list) std::list<int>;

%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *array_out, int array_length_out)}
%apply (double *IN_ARRAY1, int DIM1) {(double *array_in, int array_length_in)}

%include "aml_core.hpp"
