#include "evaluator.hpp"


class ConditionalExpression
{
public:
  std::vector<ExpressionBase*> conditions;
  std::vector<ExpressionBase*> exprs;

  ConditionalExpression() = default;
  ConditionalExpression(const ConditionalExpression&) = delete;
  ConditionalExpression &operator=(const ConditionalExpression&) = delete;
  ~ConditionalExpression();
  void add_condition(ExpressionBase* condition, ExpressionBase* expr);
  void add_final_expr(ExpressionBase* expr);
};


class Constraint
{
public:
  Evaluator** conditions;
  Evaluator** exprs;
  Var** vars;
  int num_vars = 0;
  int num_conditions = 0;
  int index = -1;
  std::string name;
  
  Constraint(ExpressionBase* expr);
  Constraint(ConditionalExpression* conditional_expr);
  Constraint(const Constraint&) = delete;
  Constraint &operator=(const Constraint&) = delete;
  ~Constraint();
  double evaluate();
  void rad();
  std::string __str__();
  std::vector<Var*> py_get_vars();
  std::set<Var*> get_var_set();
  double ad(Var*);
private:
  void set_vars();
};


