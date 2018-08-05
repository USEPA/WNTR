#include <iostream>
#include <vector>
#include <list>
#include <cmath>
#include <unordered_map>
#include <stdexcept>
#include <memory>
#include <unordered_set>
#include <sstream>
#include <iterator>
#include <iostream>
#include <cassert>
#include <stdexcept>
#include <iterator>

class Node;
class Var;
class Param;
class Expression;
class Summation;
class VarVarMultiplyOperator;
class VarParamMultiplyOperator;
class VarOperatorMultiplyOperator;
class ParamVarMultiplyOperator;
class ParamParamMultiplyOperator;
class ParamOperatorMultiplyOperator;
class OperatorVarMultiplyOperator;
class OperatorParamMultiplyOperator;
class OperatorOperatorMultiplyOperator;
class VarVarDivideOperator;
class VarParamDivideOperator;
class VarOperatorDivideOperator;
class ParamVarDivideOperator;
class ParamParamDivideOperator;
class ParamOperatorDivideOperator;
class OperatorVarDivideOperator;
class OperatorParamDivideOperator;
class OperatorOperatorDivideOperator;
class VarVarPowerOperator;
class VarParamPowerOperator;
class VarOperatorPowerOperator;
class ParamVarPowerOperator;
class ParamParamPowerOperator;
class ParamOperatorPowerOperator;
class OperatorVarPowerOperator;
class OperatorParamPowerOperator;
class OperatorOperatorPowerOperator;


std::shared_ptr<Var> create_var(double value=0.0, double lb=-1.0e100, double ub=1.0e100);


std::shared_ptr<Param> create_param(double value=0.0);


class Node: public std::enable_shared_from_this<Node>
{
public:
  Node() = default;
  virtual ~Node() = default;
  double value = 0.0;
  double der_n1 = 0.0;
  double der_n2 = 0.0;
  double der2 = 0.0;
  bool has_der_n1 = 0;
  bool has_der_n2 = 0;
  bool has_der2 = 0;
  int index = -1;
  virtual std::shared_ptr<std::vector<std::shared_ptr<Node> > > get_nodes();
  virtual std::shared_ptr<std::vector<double> > get_coefs();
  virtual std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > get_sparsity();
  virtual std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > get_vars();
  virtual std::unordered_set<std::shared_ptr<Var> > py_get_vars();
  virtual double evaluate() = 0;
  virtual double ad(Var&, bool new_eval=true) = 0;
  virtual double ad2(Var&, Var&, bool) = 0;
  virtual bool has_ad(Var&);
  virtual bool has_ad2(Var&, Var&) = 0;
  virtual std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) = 0;
  virtual std::string get_type();
  virtual void set_coefs(std::shared_ptr<std::vector<double> >);

  std::shared_ptr<Node> operator+(Node&);
  std::shared_ptr<Node> operator-(Node&);
  std::shared_ptr<Node> operator*(Node&);
  std::shared_ptr<Node> operator/(Node&);
  std::shared_ptr<Node> operator-();
  std::shared_ptr<Node> __pow__(Node&);

  std::shared_ptr<Node> operator+(double);
  std::shared_ptr<Node> operator-(double);
  std::shared_ptr<Node> operator*(double);
  std::shared_ptr<Node> operator/(double);
  std::shared_ptr<Node> __pow__(double);

  std::shared_ptr<Node> __radd__(double);
  std::shared_ptr<Node> __rsub__(double);
  std::shared_ptr<Node> __rmul__(double);
  std::shared_ptr<Node> __rdiv__(double);
  std::shared_ptr<Node> __rtruediv__(double);
  std::shared_ptr<Node> __rpow__(double);

  virtual std::shared_ptr<Node> add_const(double);
  virtual void multiply_const(double);

  std::string _print();
};


class Summation: public Node
{
public:
  Summation() = default;
  std::shared_ptr<std::vector<std::shared_ptr<Node> > > get_nodes() override;
  std::shared_ptr<std::vector<double> > get_coefs() override;
  std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > get_sparsity() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > get_vars() override;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad(Var&) override;
  bool has_ad2(Var&, Var&) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::string get_type() override;
  void set_coefs(std::shared_ptr<std::vector<double> >) override;
  std::shared_ptr<std::vector<std::shared_ptr<Node> > > nodes = std::make_shared<std::vector<std::shared_ptr<Node> > >();
  std::shared_ptr<std::vector<double> > coefs = std::make_shared<std::vector<double> >();
  std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > sparsity = std::make_shared<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > >();
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > vars = std::make_shared<std::unordered_set<std::shared_ptr<Var> > >();
  double constant = 0.0;
  std::shared_ptr<Node> add_const(double) override;
  void multiply_const(double) override;
};

class Var: public Node
{
public:
  Var() = default;
  double lb = -1.0e20;
  double ub = 1.0e20;
  double lb_dual = 0.0;
  double ub_dual = 0.0;
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > get_vars() override;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad2(Var&, Var&) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::string get_type() override;
  std::string name;
};


class Param: public Node
{
public:
  Param() = default;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad2(Var&, Var&) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::string get_type() override;
  std::string name;
};


class Expression: public Node
{
public:
  Expression() = default;  // default constructor
  std::shared_ptr<std::vector<std::shared_ptr<Node> > > get_nodes() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > get_vars() override;
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  bool has_ad(Var&) override;
  bool has_ad2(Var&, Var&) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::string get_type() override;
  std::shared_ptr<std::vector<std::shared_ptr<Node> > > nodes = std::make_shared<std::vector<std::shared_ptr<Node> > >();
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > vars = std::make_shared<std::unordered_set<std::shared_ptr<Var> > >();
};


class VarVarMultiplyOperator: public Node
{
public:
  VarVarMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarParamMultiplyOperator: public Node
{
public:
  VarParamMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarOperatorMultiplyOperator: public Node
{
public:
  VarOperatorMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamVarMultiplyOperator: public Node
{
public:
  ParamVarMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamParamMultiplyOperator: public Node
{
public:
  ParamParamMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamOperatorMultiplyOperator: public Node
{
public:
  ParamOperatorMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorVarMultiplyOperator: public Node
{
public:
  OperatorVarMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorParamMultiplyOperator: public Node
{
public:
  OperatorParamMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorOperatorMultiplyOperator: public Node
{
public:
  OperatorOperatorMultiplyOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarVarDivideOperator: public Node
{
public:
  VarVarDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarParamDivideOperator: public Node
{
public:
  VarParamDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarOperatorDivideOperator: public Node
{
public:
  VarOperatorDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamVarDivideOperator: public Node
{
public:
  ParamVarDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamParamDivideOperator: public Node
{
public:
  ParamParamDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamOperatorDivideOperator: public Node
{
public:
  ParamOperatorDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorVarDivideOperator: public Node
{
public:
  OperatorVarDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorParamDivideOperator: public Node
{
public:
  OperatorParamDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorOperatorDivideOperator: public Node
{
public:
  OperatorOperatorDivideOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarVarPowerOperator: public Node
{
public:
  VarVarPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarParamPowerOperator: public Node
{
public:
  VarParamPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class VarOperatorPowerOperator: public Node
{
public:
  VarOperatorPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamVarPowerOperator: public Node
{
public:
  ParamVarPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamParamPowerOperator: public Node
{
public:
  ParamParamPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class ParamOperatorPowerOperator: public Node
{
public:
  ParamOperatorPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorVarPowerOperator: public Node
{
public:
  OperatorVarPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorParamPowerOperator: public Node
{
public:
  OperatorParamPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};


class OperatorOperatorPowerOperator: public Node
{
public:
  OperatorOperatorPowerOperator(std::shared_ptr<Node> n1, std::shared_ptr<Node> n2): node1(n1), node2(n2) {}
  double evaluate() override;
  double ad(Var&, bool new_eval=true) override;
  double ad2(Var&, Var&, bool) override;
  std::string set_name(std::unordered_map<std::shared_ptr<Node>, std::string>&) override;
  std::shared_ptr<Node> node1;
  std::shared_ptr<Node> node2;
  bool has_ad2(Var&, Var&) override;
};
