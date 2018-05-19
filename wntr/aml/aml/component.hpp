#include "expression.hpp"

class Component;
class Constraint;
class Objective;
class ConditionalConstraint;


std::shared_ptr<Constraint> create_constraint(std::shared_ptr<Node> expr, double lb=-1e100, double ub=1e100);
std::shared_ptr<ConditionalConstraint> create_conditional_constraint(double lb=-1e100, double ub=1e100);
std::shared_ptr<Objective> create_objective(std::shared_ptr<Node> expr);


class Component
{
public:
  Component() = default;
  virtual ~Component() = default;
  virtual double evaluate() = 0;
  virtual double ad(Var&, bool new_eval=true) = 0;
  virtual double ad2(Var&, Var&, bool) = 0;
  virtual bool has_ad2(Var&, Var&) = 0;
  virtual std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() = 0;
  virtual std::set<std::shared_ptr<Var> > py_get_vars();
  virtual std::string _print() = 0;
  int index = -1;
  double value = 0.0;
  std::string name;
};


class Objective: public Component
{
public:
  Objective() = default;
  explicit Objective(std::shared_ptr<Node> e): expr(e) {}
  std::shared_ptr<Node> expr;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad2(Var&, Var&) override;
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
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
  explicit Constraint(std::shared_ptr<Node> e): expr(e) {}
  std::shared_ptr<Node> expr;
  double get_dual() override;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad2(Var&, Var&) override;
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
};


class ConditionalConstraint: public ConstraintBase
{
public:
  ConditionalConstraint() = default;
  std::vector<std::shared_ptr<Node> > condition_exprs;
  std::vector<std::shared_ptr<Node> > exprs;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad2(Var&, Var&) override;
  void add_condition(std::shared_ptr<Node>, std::shared_ptr<Node>);
  void add_final_expr(std::shared_ptr<Node>);
  double get_dual() override;
  std::string _print() override;
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars() override;
};