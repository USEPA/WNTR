#include "component.hpp"

class CoreModel;


class WNTRModel
{
public:
  std::unordered_set<std::shared_ptr<Var> > vars;
  std::unordered_set<std::shared_ptr<ConstraintBase> > cons;
  std::vector<std::shared_ptr<ConstraintBase> > cons_vector;
  std::vector<std::shared_ptr<Var> > vars_vector;
  bool is_structure_fixed = false;
  int nnz = 0;
  void get_x(double *array_out, int array_length_out);
  void load_var_values_from_x(double *array_in, int array_length_in);
  void add_constraint(std::shared_ptr<ConstraintBase>);
  void remove_constraint(std::shared_ptr<ConstraintBase>);
  void add_var(std::shared_ptr<Var>);
  void remove_var(std::shared_ptr<Var>);
  void evaluate(double *array_out, int array_length_out);
  void evaluate_csr_jacobian(double *values_array_out, int values_array_length_out, int *col_ndx_array_out, int col_ndx_array_length_out, int *row_nnz_array_out, int row_nnz_array_length_out, bool new_eval=true);
  void set_structure();
  void release_structure();
};
