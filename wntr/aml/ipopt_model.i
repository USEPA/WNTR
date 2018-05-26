%module ipopt_model
%feature("kwargs");
%feature("autodoc","3");
%{
  #include "ipopt_model.hpp"
%}

%include "std_string.i"
%include "ipopt_model.hpp"
