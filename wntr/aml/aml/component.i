%module component
%include <std_shared_ptr.i>
%shared_ptr(Constraint)
%shared_ptr(ConditionalConstraint)
%shared_ptr(ConstraintBase)
%shared_ptr(Objective)
%shared_ptr(Component)
%feature("kwargs");
%feature("autodoc","3");
%{
  #include "component.hpp"
%}

%include "std_string.i"
%include "component.hpp"
