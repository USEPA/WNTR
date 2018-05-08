#include "expression.hpp"

class Component
class Constraint
class Objective
class ConditionalConstraint


std::shared_ptr<Constraint> create_constraint(std::shared_ptr<Node>);
std::shared_ptr<ConditionalConstraint> create_conditional_constraint();
std::shared_ptr<Objective> create_objective(std::shared_ptr<Node>);


class Component
{
public:
  Component() = default;
  virtual ~Component() = default;
  virtual double evaluate() = 0;
  virtual double ad(Var&, bool) = 0;
  virtual double ad2(Var&, Var&, bool) = 0;
  virtual std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() = 0;
  virtual std::string _print() = 0;
  int index = -1;
  std::string name;
}


class Objective
{
public:
  Objective() = default;
  explicit Objective(std::shared_ptr<Node> e): expr(e) {}
  std::shared_ptr<Node> expr;
  double evaluate() override;
  double ad(Var&, bool) override;
  double ad2(Var&, Var&, bool) override;
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
}


class Constraint
{
public:
  Constraint() = default;
  explicit Constraint(std::shared_ptr<Node> e): expr(e) {}
  std::shared_ptr<Node> expr;
  double lb = -1.0e20;
  double ub = 1.0e20;
  double dual = 0.0;
  double get_dual();
  double evaluate() override;
  double ad(Var&, bool) override;
  double ad2(Var&, Var&, bool) override;
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
}


class ConditionalConstraint
{
public:
  ConditionalConstraint() = default;
  std::vector<std::shared_ptr<Node> > condition_exprs;
  std::vector<std::shared_ptr<Node> > exprs;
  double evaluate() override;
  double ad(Var&, bool) override;
  double ad2(Var&, Var&, bool) override;
  void add_condition(std::shared_ptr<Node>, std::shared_ptr<Node>);
  void add_final_expr(std::shared_ptr<Node>);
  double lb = -1.0e20;
  double ub = 1.0e20;
  double dual = 0.0;
  double get_dual();
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
}