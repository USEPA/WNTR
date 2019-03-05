#include <vector>
#include <iostream>
#include <set>
#include <map>
#include <stdexcept>


const int ADD = -1;
const int SUB = -2;
const int MUL = -3;
const int DIV = -4;
const int POW = -5;
const int ABS = -6;
const int SIGN = -7;
const int IF_ELSE = -8;
const int INEQUALITY = -9;


class Leaf
{
public:
  Leaf() = default;
  Leaf(double val): value(val) {}
  virtual ~Leaf() = default;

  double value = 0;
};


class Var: public Leaf
{
public:
  Var() = default;
  Var(double val): Leaf(val) {}
  ~Var() = default;
};


class Param: public Leaf
{
public:
  Param() = default;
  Param(double val): Leaf(val) {}
  ~Param() = default;
};


class Float: public Leaf
{
public:
  Float() = default;
  Float(double val): Leaf(val) {}
  ~Float() = default;
};


class Constraint
{
public:
  Constraint() = default;
  ~Constraint() = default;

  void add_leaf(Leaf* leaf);
  void add_fn_rpn_term(int term);
  void add_jac_rpn_term(Var* v, int term);

  std::vector<int> fn_rpn;
  std::map<Var*, std::vector<int> > jac_rpn;
  std::vector<Leaf*> leaves;
}


class Evaluator
{
public:
  Evaluator() = default;
  ~Evaluator() = default;

  Var* add_var(double value);
  Param* add_param(double value);
  Float* add_float(double value);
  Constraint* add_constraint();

  void remove_var(Var* v);
  void remove_param(Param* p);
  void remove_float(Float* f);
  void remove_constraint(Constraint* c);

  void set_structure();
  void release_structure();

  void evaluate(double* array_out, int array_length_out);
  void evaluate_csr_jacobian(double* values_array_out, int values_array_length_out, int* col_ndx_array_out, int col_ndx_array_length_out, int* row_nnz_array_out, int row_nnz_array_length_out);

private:
  std::set<Var> var_set;
  std::set<Param> param_set;
  std::set<Float> float_set;
  std::set<Constraint> con_set;

  std::vector<Var*> var_vector;
  
  std::vector<std::vector<int> > fn_rpn;
  std::vector<std::vector<double*> > fn_leaf_values;

  std::vector<std::vector<int> > jac_rpn;
  std::vector<std::vector<double*> > jac_leaf_values;
  std::vector<int> col_ndx;
  std::vector<int> row_nnz;
};


double evaluate(std::vector<int>* rpn, std::vector<double*>* values);
