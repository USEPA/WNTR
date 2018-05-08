%module ipopt_model
%include <std_shared_ptr.i>
%shared_ptr(IpoptConstraint)
%shared_ptr(IpoptObjective)
%shared_ptr(IpoptComponent)
%{
  #include "ipopt_model.hpp"
%}

%include "std_string.i"
%include "ipopt_model.hpp"
