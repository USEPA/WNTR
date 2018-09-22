#include "expression.hpp"

class Component;
class Constraint;
class Objective;
class ConditionalConstraint;


std::shared_ptr<Constraint> create_constraint(std::shared_ptr<ExpressionBase> expr, double lb=-1e100, double ub=1e100);
std::shared_ptr<ConditionalConstraint> create_conditional_constraint(double lb=-1e100, double ub=1e100);
std::shared_ptr<Objective> create_objective(std::shared_ptr<ExpressionBase> expr);


class Component
{
public:
  Component() = default;
  virtual ~Component() = default;
  virtual double evaluate() = 0;
  virtual void rad(bool new_eval=true) = 0;
  virtual std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() = 0;
  virtual std::unordered_set<std::shared_ptr<ExpressionBase> > py_get_vars();
  virtual std::string __str__() = 0;
  int index = -1;
  std::string name;
};


class Objective: public Component
{
public:
  Objective() = default;
  explicit Objective(std::shared_ptr<ExpressionBase> e): expr(e) {}
  std::shared_ptr<ExpressionBase> expr;
  double evaluate() override;
  void rad(bool new_eval=true) override;
  std::string __str__() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() override;
};


class ConstraintBase: public Component
{
public:
  ConstraintBase() = default;
  virtual ~ConstraintBase() = default;
  double lb = -1.0e100;
  double ub = 1.0e100;
  double dual = 0.0;
  virtual double get_dual() = 0;
};


class Constraint: public ConstraintBase
{
public:
  Constraint() = default;
  explicit Constraint(std::shared_ptr<ExpressionBase> e): expr(e) {}
  std::shared_ptr<ExpressionBase> expr;
  double get_dual() override;
  double evaluate() override;
  void rad(bool new_eval=true) override;
  std::string __str__() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() override;
};


class ConditionalConstraint: public ConstraintBase
{
public:
  ConditionalConstraint() = default;
  std::vector<std::shared_ptr<ExpressionBase> > condition_exprs;
  std::vector<std::shared_ptr<ExpressionBase> > exprs;
  double evaluate() override;
  void rad(bool new_eval=true) override;
  void add_condition(std::shared_ptr<ExpressionBase>, std::shared_ptr<ExpressionBase>);
  void add_final_expr(std::shared_ptr<ExpressionBase>);
  double get_dual() override;
  std::string __str__() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() override;
};
