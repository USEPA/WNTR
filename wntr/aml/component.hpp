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
  int num_conditions = 0;
  int index = -1;
  std::string name;
  
  Constraint(ExpressionBase* expr);
  Constraint(ConditionalExpression* conditional_expr);
  Constraint(const Constraint&) = delete;
  Constraint &operator=(const Constraint&) = delete;
  ~Constraint();
  double evaluate();
  std::shared_ptr<std::unordered_map<Leaf*, double> > rad();
  std::string __str__();
  std::shared_ptr<std::unordered_set<Var*> > get_vars();
};


