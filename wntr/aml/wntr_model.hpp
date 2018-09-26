#include "component.hpp"


class WNTRModel
{
public:
  std::unordered_set<Var*> vars;
  std::set<Constraint*> cons;
  std::vector<Constraint*> cons_vector;
  std::vector<Var*> vars_vector;
  bool is_structure_fixed = false;
  int nnz = 0;
  void get_x(double *array_out, int array_length_out);
  void load_var_values_from_x(double *array_in, int array_length_in);
  void add_constraint(Constraint*);
  void remove_constraint(Constraint*);
  void add_var(ExpressionBase*);
  void remove_var(ExpressionBase*);
  void evaluate(double *array_out, int array_length_out);
  void evaluate_csr_jacobian(double *values_array_out, int values_array_length_out, int *col_ndx_array_out, int col_ndx_array_length_out, int *row_nnz_array_out, int row_nnz_array_length_out);
  void set_structure();
  void release_structure();
};
