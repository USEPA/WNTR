#include "component.hpp"

class IpoptModel;


class IpoptModel
{
public:
  void add_constraint(std::shared_ptr<ConstraintBase>);
  void remove_constraint(std::shared_ptr<ConstraintBase>);
  void add_var(std::shared_ptr<Var>);
  void remove_var(std::shared_ptr<Var>);
  void set_objective(std::shared_ptr<Objective>);
  void solve();
  std::shared_ptr<Objective> obj = nullptr;
  std::unordered_set<std::shared_ptr<Var> > vars;
  std::unordered_set<std::shared_ptr<ConstraintBase> > cons;
  std::vector<std::shared_ptr<Var> > vars_vector;
  std::vector<std::shared_ptr<ConstraintBase> > cons_vector;
  std::string solver_status;
  std::unordered_map<std::shared_ptr<Var>, std::unordered_map<std::shared_ptr<Var>, std::unordered_map<std::string, std::unordered_set<std::shared_ptr<Component> > > > > hessian_map;
  std::vector<std::shared_ptr<Var> > hessian_vector_var1;
  std::vector<std::shared_ptr<Var> > hessian_vector_var2;
};
