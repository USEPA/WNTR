#include "expression.hpp"

class IpoptComponent;
class IpoptObjective;
class IpoptConstraint;
class IpoptModel;

class IpoptComponent
{
public:
  std::shared_ptr<Node> expr;
  IpoptComponent() = default;
  explicit IpoptComponent(std::shared_ptr<Node> e): expr(e) {}
  virtual ~IpoptComponent() = default;
  int index = -1;
};


class IpoptObjective: public IpoptComponent
{
public:
  IpoptObjective() = default;
  explicit IpoptObjective(std::shared_ptr<Node> e): IpoptComponent(e) {}
};


class IpoptConstraint: public IpoptComponent
{
public:
  IpoptConstraint() = default;
  explicit IpoptConstraint(std::shared_ptr<Node> e, double lower, double upper): IpoptComponent(e), lb(lower), ub(upper) {}
  explicit IpoptConstraint(std::shared_ptr<Node> e, std::string lower, double upper): IpoptComponent(e), ub(upper) {}
  explicit IpoptConstraint(std::shared_ptr<Node> e, double lower, std::string upper): IpoptComponent(e), lb(lower) {}
  double lb = -1.0e20;
  double ub = 1.0e20;
  double dual = 0.0;
  std::string name;
  double evaluate();
  double ad(Var&, bool);
  double ad2(Var&, Var&, bool);
  std::shared_ptr<std::set<std::shared_ptr<Var> > > get_vars();
  std::string _print();
  double get_dual();
};


std::shared_ptr<IpoptConstraint> create_ipopt_constraint(std::shared_ptr<Node>);
std::shared_ptr<IpoptObjective> create_ipopt_objective(std::shared_ptr<Node>);


class IpoptModel
{
public:
  void add_constraint(std::shared_ptr<IpoptConstraint>);
  void remove_constraint(std::shared_ptr<IpoptConstraint>);
  void add_var(std::shared_ptr<Var>);
  void remove_var(std::shared_ptr<Var>);
  void set_objective(std::shared_ptr<IpoptObjective>);
  void solve();
  std::shared_ptr<IpoptObjective> obj = nullptr;
  std::list<std::shared_ptr<Var> > vars;
  std::list<std::shared_ptr<IpoptConstraint> > cons;
  std::string solver_status;
  std::map<std::shared_ptr<Var>, std::map<std::shared_ptr<Var>, std::map<std::string, std::set<std::shared_ptr<IpoptComponent> > > > > hessian_map;
};
