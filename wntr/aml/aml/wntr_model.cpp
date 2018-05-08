#include "wntr_model.hpp"

void CoreModel::get_x(double *array_out, int array_length_out)
{
    int i = 0;
    for (Var* &v_ptr : vars)
    {
        array_out[i] = v_ptr->value;
        ++i;
    }
}


void CoreModel::load_var_values_from_x(double *arrayin, int array_length_in)
{
    int i = 0;
    for (Var* &v_ptr: vars)
    {
        v_ptr->value = arrayin[i];
        ++i;
    }
}


void CoreModel::register_constraint(ConstraintBase *con)
{
    cons.push_back(con);
    jac.register_constraint(con);
}


void CoreModel::remove_constraint(ConstraintBase *con)
{
    auto cons_iterator = cons.begin();
    std::advance(cons_iterator, con->index);
    cons.erase(cons_iterator);
    jac.remove_constraint(con);
}


void CoreModel::evaluate(double *array_out, int array_length_out)
{
    int i = 0;
    for (auto &ptr_to_con : cons)
    {
        array_out[i] = ptr_to_con->evaluate();
        ++i;
    }
}


void CoreModel::recursive_evaluate(double *array_out, int array_length_out)
{
    int i = 0;
    for (auto &ptr_to_con : cons)
    {
        array_out[i] = ptr_to_con->recursive_evaluate();
        ++i;
    }
}


bool compare_var_indices(Var *first, Var *second)
{
    return (first->index < second->index);
}


void CSRJacobian::register_constraint(ConstraintBase *con)
{
    //  Gather some needed data
    int last_row_nnz = row_nnz.back();
    int n_vars = (con->vars()).size();

    //  Now add the number of nonzero elements to row_nnz
    row_nnz.push_back(n_vars + last_row_nnz);

    //  Now add the constraint to cons;
    for (int i = 0; i < n_vars; ++i)
    {
        cons.push_back(con);
    }

    //  Now add the vars and the column indices
    std::list<Var*> vars_to_add;
    for (auto &v : con->vars())
    {
        vars_to_add.push_back(v);
    }
    vars_to_add.sort(compare_var_indices);
    for (auto &v : vars_to_add)
    {
        vars.push_back(v);
        col_ndx.push_back(v->index);
    }
}


void CSRJacobian::remove_constraint(ConstraintBase *con)
{
    //  First create the iterators for row_nnz, col_ndx, vars, and cons;
    auto row_nnz_iterator = row_nnz.begin();
    auto col_ndx_iterator = col_ndx.begin();
    auto col_ndx_iterator2 = col_ndx.begin();
    auto vars_iterator = vars.begin();
    auto vars_iterator2 = vars.begin();
    auto cons_iterator = cons.begin();
    auto cons_iterator2 = cons.begin();

    //  Gather some needed data
    std::advance(row_nnz_iterator, con->index);
    int last_row_nnz = *row_nnz_iterator;
    int n_vars = (con->vars()).size();

    //  Now remove the number of nonzero elements from row_nnz
    ++row_nnz_iterator;
    row_nnz_iterator = row_nnz.erase(row_nnz_iterator);
    while (row_nnz_iterator != row_nnz.end())
    {
        (*row_nnz_iterator) -= n_vars;
        ++row_nnz_iterator;
    }

    //  Now remove the constraint from cons;
    std::advance(cons_iterator, last_row_nnz);
    std::advance(cons_iterator2, last_row_nnz + n_vars);
    cons.erase(cons_iterator, cons_iterator2);

    //  Now remove the vars and the column indices
    std::advance(col_ndx_iterator, last_row_nnz);
    std::advance(col_ndx_iterator2, last_row_nnz + n_vars);
    std::advance(vars_iterator, last_row_nnz);
    std::advance(vars_iterator2, last_row_nnz + n_vars);
    col_ndx.erase(col_ndx_iterator, col_ndx_iterator2);
    vars.erase(vars_iterator, vars_iterator2);
}


void CSRJacobian::evaluate(double *array_out, int array_length_out)
{
    auto con_iter = cons.begin();
    auto var_iter = vars.begin();
    int i = 0;

    while (con_iter != cons.end() && var_iter != vars.end())
    {
        array_out[i] = (*con_iter)->ad(*(*var_iter));
        ++con_iter;
        ++var_iter;
        ++i;
    }
}


void CSRJacobian::recursive_evaluate(double *array_out, int array_length_out)
{
    auto con_iter = cons.begin();
    auto var_iter = vars.begin();
    int con_size = cons.size();
    int i = 0;

    for (; i < con_size; ++i)
    {
        array_out[i] = (*con_iter)->recursive_ad(*(*var_iter));
        ++con_iter;
        ++var_iter;
    }
}


std::list<int> CSRJacobian::get_col_ndx()
{
    return col_ndx;
}


std::list<int> CSRJacobian::get_row_nnz()
{
    return row_nnz;
}


