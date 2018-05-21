%module component
%include <std_shared_ptr.i>
%shared_ptr(Constraint)
%shared_ptr(ConditionalConstraint)
%shared_ptr(ConstraintBase)
%shared_ptr(Objective)
%shared_ptr(Component)
%shared_ptr(var_set)
%feature("kwargs");
%feature("autodoc","3");
%{
  #include "component.hpp"
%}

%include "std_string.i"
%include "std_set.i"
%template(var_set) std::set<std::shared_ptr<Var> >;
%include "component.hpp"
