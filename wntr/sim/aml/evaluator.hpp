#include <vector>
#include <iostream>
#include <set>
#include <map>
#include <stdexcept>
#include <cmath>


const int ADD = -1;
const int SUB = -2;
const int MUL = -3;
const int DIV = -4;
const int POW = -5;
const int ABS = -6;
const int SIGN = -7;
const int IF_ELSE = -8;
const int INEQUALITY = -9;
const int EXP = -10;
const int LOG = -11;
const int NEGATION = -12;
const int SIN = -13;
const int COS = -14;
const int TAN = -15;
const int ASIN = -16;
const int ACOS = -17;
const int ATAN = -18;


class StructureException: public std::exception
{
public:
  StructureException() {msg = "StructureException";}
  StructureException(std::string const &message) : msg(message) {}
  ~StructureException() throw() {}
  virtual const char* what() const throw()
  {
    return msg.c_str();
  }
private:
  std::string msg;
};


class Leaf
{
public:
  Leaf(){}
  Leaf(double val): value(val) {}
  virtual ~Leaf(){}

  double value;
};


class Var: public Leaf
{
public:
  Var(){}
  Var(double val): Leaf(val) {}
  ~Var(){}

  int index;
};


class Param: public Leaf
{
public:
  Param(){}
  Param(double val): Leaf(val) {}
  ~Param(){}
};


class Float: public Leaf
{
public:
  Float(){}
  Float(double val): Leaf(val) {}
  ~Float(){}
};


class Constraint
{
public:
  Constraint(){}
  ~Constraint(){}

  void add_leaf(Leaf* leaf);
  void add_fn_rpn_term(int term);
  void add_jac_rpn_term(Var* v, int term);

  std::vector<int> fn_rpn;
  std::map<Var*, std::vector<int> > jac_rpn;
  std::vector<Leaf*> leaves;

  int index;
};


class IfElseConstraint
{
public:
  IfElseConstraint(){}
  ~IfElseConstraint(){}

  void add_leaf(Leaf* leaf);
  void end_condition();
  void add_condition_rpn_term(int term);
  void add_fn_rpn_term(int term);
  void add_jac_rpn_term(Var* v, int term);

  std::vector<int> current_condition_rpn;
  std::vector<int> current_fn_rpn;
  std::map<Var*, std::vector<int> > current_jac_rpn;
  
  std::vector<std::vector<int> > condition_rpn;
  std::vector<std::vector<int> > fn_rpn;
  std::map<Var*, std::vector<std::vector<int> > > jac_rpn;

  std::vector<Leaf*> leaves;

  int index;
};


class Evaluator
{
public:
  Evaluator(){is_structure_set = false;}
  ~Evaluator();

  int nnz;
  double* stack;

  Var* add_var(double value);
  Param* add_param(double value);
  Float* add_float(double value);
  Constraint* add_constraint();
  IfElseConstraint* add_if_else_constraint();

  void remove_var(Var* v);
  void remove_param(Param* p);
  void remove_float(Float* f);
  void remove_constraint(Constraint* c);
  void remove_if_else_constraint(IfElseConstraint* c);

  void set_structure();
  void remove_structure();

  void get_x(double *array_out, int array_length_out);
  void load_var_values_from_x(double *array_in, int array_length_in);

  void evaluate(double* array_out, int array_length_out);
  void evaluate_csr_jacobian(double* values_array_out, int values_array_length_out, int* col_ndx_array_out, int col_ndx_array_length_out, int* row_nnz_array_out, int row_nnz_array_length_out);

private:
  bool is_structure_set;
  
  std::set<Var*> var_set;
  std::set<Param*> param_set;
  std::set<Float*> float_set;
  std::set<Constraint*> con_set;
  std::set<IfElseConstraint*> if_else_con_set;

  std::vector<Var*> var_vector;
  std::vector<std::vector<Leaf*> > leaves;
  std::vector<int> col_ndx;
  std::vector<int> row_nnz;

  std::vector<std::vector<int> > fn_rpn;
  std::vector<std::vector<int> > jac_rpn;

  std::vector<int> n_conditions;
  std::vector<std::vector<int> > if_else_condition_rpn;
  std::vector<std::vector<int> > if_else_fn_rpn;
  std::vector<std::vector<int> > if_else_jac_rpn;
};


double _evaluate(double* stack, std::vector<int>* rpn, std::vector<Leaf*>* values);
