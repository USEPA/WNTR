%module aml_core
%include <std_shared_ptr.i>
%shared_ptr(var_set)
%feature("kwargs");
%feature("autodoc","3");
%{
  #define SWIG_FILE_WITH_INIT
  #include "wntr_model.hpp"
%}

%include "std_string.i"
%include "pyabc.i"
%include "std_vector.i"
%include "std_set.i"
%template(var_set) std::set<Var*>;
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

%include "expression.hpp"
%include "evaluator.hpp"
%include "component.hpp"
%include "wntr_model.hpp"
