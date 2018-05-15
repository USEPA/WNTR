#include "component.hpp"

class CSRJacobian;
class CoreModel;


class CSRJacobian  //  Compressed sparse row format
{
public:
    std::list<int> row_nnz = {0};  // row_nnz[i+1] - row_nnz[i] is the number of nonzeros in row i (constraint with index i)
    std::list<int> col_ndx;  // the column index (aka the Var index)
    std::list<std::shared_ptr<Var> > vars;  // A list of pointers to the variables with respect to which differentiation should be done.

    // The constraints; Differentiate these wrt the corresponding var in vars to get the values of the CSR matrix
    std::list<std::shared_ptr<Component> > cons;

    void register_constraint(std::shared_ptr<Component>);
    void remove_constraint(std::shared_ptr<Component>);
    void evaluate(double *array_out, int array_length_out);
    std::list<int> get_row_nnz();
    std::list<int> get_col_ndx();
};


class WNTRModel
{
public:
    std::list<std::shared_ptr<Var> > vars;
    std::list<std::shared_ptr<Component> > cons;
    CSRJacobian jac;
    void get_x(double *array_out, int array_length_out);
    void load_var_values_from_x(double *array_in, int array_length_in);
    void register_constraint(std::shared_ptr<Component>);
    void remove_constraint(std::shared_ptr<Component>);
    void evaluate(double *array_out, int array_length_out);
};


bool compare_var_indices(std::shared_ptr<Var>, std::shared_ptr<Var>);

