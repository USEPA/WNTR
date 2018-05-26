%module wntr_model
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

%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *array_out, int array_length_out)}
%apply (double *IN_ARRAY1, int DIM1) {(double *array_in, int array_length_in)}

%include "wntr_model.hpp"
