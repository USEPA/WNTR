#include "expression.hpp"

class ConstraintBase;
class Constraint;
class ConditionalConstraint;
class CSRJacobian;
class CoreModel;


class ConstraintBase
{
public:
    ConstraintBase() = default;
    virtual ~ConstraintBase() = default;
    virtual double evaluate() = 0;
    virtual double ad(Var&) = 0;
    virtual double ad2(Var&, Var&) = 0;
    virtual double recursive_ad(Var&) = 0;
    virtual double recursive_ad2(Var&, Var&) = 0;
    virtual double recursive_evaluate() = 0;
    virtual std::set<Var*> vars() = 0;
    int index = -1;
    std::string name;
    virtual std::string _print() = 0;
};


class Constraint: public ConstraintBase
{
public:
    Constraint() = default;
    explicit Constraint(Expression e): expr(e) {}
    explicit Constraint(Var &v): expr(v) {}
    Expression expr;
    double evaluate() override;
    double ad(Var&) override;
    double ad2(Var&, Var&) override;
    std::set<Var*> vars() override;
    std::string _print() override;
    double recursive_ad(Var&) override;
    double recursive_ad2(Var&, Var&) override;
    double recursive_evaluate() override;
};


class ConditionalConstraint: public ConstraintBase
{
public:
    ConditionalConstraint() = default;
    std::vector<Expression> condition_exprs;
    std::vector<Expression> exprs;
    double evaluate() override;
    double ad(Var&) override;
    double ad2(Var&, Var&) override;
    void add_condition(Expression condition, Expression expr);
    void add_condition(Var &condition, Expression expr);
    void add_condition(Expression condition, Var &expr);
    void add_condition(Var &condition, Var &expr);
    void add_final_expr(Expression expr);
    void add_final_expr(Var &expr);
    std::set<Var*> vars() override;
    std::string _print() override;
    double recursive_ad(Var&) override;
    double recursive_ad2(Var&, Var&) override;
    double recursive_evaluate() override;
};


class CSRJacobian  //  Compressed sparse row format
{
public:
    std::list<int> row_nnz = {0};  // row_nnz[i+1] - row_nnz[i] is the number of nonzeros in row i (constraint with index i)
    std::list<int> col_ndx;  // the column index (aka the Var index)
    std::list<Var*> vars;  // A list of pointers to the variables with respect to which differentiation should be done.

    // The constraints; Differentiate these wrt the corresponding var in vars to get the values of the CSR matrix
    std::list<ConstraintBase*> cons;

    void register_constraint(ConstraintBase*);
    void remove_constraint(ConstraintBase*);
    void evaluate(double *array_out, int array_length_out);
    void recursive_evaluate(double *array_out, int array_length_out);
    std::list<int> get_row_nnz();
    std::list<int> get_col_ndx();
};


class CoreModel
{
public:
    std::list<Var*> vars;
    std::list<ConstraintBase*> cons;
    CSRJacobian jac;
    void get_x(double *array_out, int array_length_out);
    void load_var_values_from_x(double *array_in, int array_length_in);
    void register_constraint(ConstraintBase*);
    void remove_constraint(ConstraintBase*);
    void evaluate(double *array_out, int array_length_out);
    void recursive_evaluate(double *array_out, int array_length_out);
};


bool compare_var_indices(Var*, Var*);

