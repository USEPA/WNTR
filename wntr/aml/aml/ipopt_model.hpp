#include "component.hpp"

class IpoptModel;


class IpoptModel
{
public:
  void add_constraint(std::shared_ptr<Component>);
  void remove_constraint(std::shared_ptr<Component>);
  void add_var(std::shared_ptr<Var>);
  void remove_var(std::shared_ptr<Var>);
  void set_objective(std::shared_ptr<Objective>);
  void solve();
  std::shared_ptr<Objective> obj = nullptr;
  std::list<std::shared_ptr<Var> > vars;
  std::list<std::shared_ptr<Component> > cons;
  std::string solver_status;
  std::map<std::shared_ptr<Var>, std::map<std::shared_ptr<Var>, std::map<std::string, std::set<std::shared_ptr<Component> > > > > hessian_map;
};
