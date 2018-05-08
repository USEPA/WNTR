#include "expression.hpp"

class IpoptModel;


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
