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
class ExpressionBase;
class Leaf;
class Var;
class Param;
class Float;
class Expression;
class Operator;
class SummationOperator;
class MultiplyOperator;
class DivideOperator;
class PowerOperator;
class SinOperator;
class CosOperator;
class TanOperator;
class AsinOperator;
class AcosOperator;
class AtanOperator;
class ExpOperator;
class LogOperator;


typedef std::unordered_map<std::shared_ptr<Node>, double> NodeDMap;
typedef std::unordered_map<std::shared_ptr<Node>, bool> NodeBMap;
typedef std::unordered_map<std::shared_ptr<Node>, std::shared_ptr<ExpressionBase> > NodeEMap;


std::unorderd_set<std::string> leaf_types;
leaf_types.insert("Var");
leaf_types.insert("Param");
leaf_types.insert("Float");


std::shared_ptr<Var> create_var(double value=0.0, double lb=-1.0e100, double ub=1.0e100);
std::shared_ptr<Param> create_param(double value=0.0);


class Node: public std::enable_shared_from_this<Node>
{
public:
  Node() = default;
  virtual ~Node() = default;
  virtual std::string get_type() = 0;
};


class ExpressionBase: public Node
{
public:
  ExpressionBase() = default;
  virtual ~ExpressionBase() = default;
  virtual std::shared_ptr<std::vector<std::shared_ptr<Operator> > > get_operators();
  virtual std::sahred_ptr<std::vector<std::shared_ptr<Var> > > get_vars();
  virtual std::string __str__() = 0;

  std::shared_ptr<ExpressionBase> operator+(ExpressionBase&);
  std::shared_ptr<ExpressionBase> operator-(ExpressionBase&);
  std::shared_ptr<ExpressionBase> operator*(ExpressionBase&);
  std::shared_ptr<ExpressionBase> operator/(ExpressionBase&);
  std::shared_ptr<ExpressionBase> operator-();
  std::shared_ptr<ExpressionBase> __pow__(ExpressionBase&);

  std::shared_ptr<ExpressionBase> operator+(double);
  std::shared_ptr<ExpressionBase> operator-(double);
  std::shared_ptr<ExpressionBase> operator*(double);
  std::shared_ptr<ExpressionBase> operator/(double);
  std::shared_ptr<ExpressionBase> __pow__(double);

  std::shared_ptr<ExpressionBase> __radd__(double);
  std::shared_ptr<ExpressionBase> __rsub__(double);
  std::shared_ptr<ExpressionBase> __rmul__(double);
  std::shared_ptr<ExpressionBase> __rdiv__(double);
  std::shared_ptr<ExpressionBase> __rtruediv__(double);
  std::shared_ptr<ExpressionBase> __rpow__(double);

  virtual double evaluate() = 0;
  virtual double ad(Var&, bool new_eval=true) = 0;
  virtual double ad2(Var&, Var&, bool new_eval=true) = 0;
  virtual bool has_ad(Var&) = 0;
  virtual bool has_ad2(Var&, Var&) = 0;
  virtual std::shared_ptr<ExpressionBase> sd(Var&, bool new_eval=true) = 0;

  virtual std::shared_ptr<ExpressionBase> add_leaf(ExpressionBase&, double coef) = 0;
  virtual std::shared_ptr<ExpressionBase> add_expr(ExpressionBase&, double coef) = 0;
};


class Operator: public Node
{
public:
  Operator() = default;
  virtual ~Operator() = default;
  virtual void evaluate(NodeDMap &val_map) = 0;
  virtual void ad(Var&, NodeDMap &val_map, NodeDMap &der_map, bool new_eval=true) = 0;
  virtual void ad2(Var&, Var&, NodeDMap &val_map, NodeDMap &der_n1_map,
		   NodeDMap &der_n2_map, NodeDMap &der2_map, bool new_eval=true) = 0;
  virtual void has_ad(Var&, NodeBMap &der_map) = 0;
  virtual void has_ad2(Var&, Var&, NodeBMap &der_n1_map, NodeBMap &der_n2_map,
		       NodeBMap &der2_map) = 0;
  virtual void sd(Var&, NodeEMap &val_map, NodeEMap &der_map, bool new_eval=true) = 0;
};


class Var: public ExpressionBase
{
public:
  Var() = default;
  ~Var() = default;
  std::string name;
  double value;
  double lb;
  double ub;

  virtual std::sahred_ptr<std::vector<std::shared_ptr<Var> > > &get_vars() override;
  std::string __str__() override;

  double evaluate() override;
  double ad(Var& bool new_eval=true) override;
  double ad2(Var&, Var&, bool new_eval=true) override;
  bool has_ad(Var&) override;
  bool has_ad2(Var&, Var&) override;
  std::shared_ptr<ExpressionBase> sd(Var&, bool new_eval=true) override;
};


class Expression: public ExpressionBase
{
public:
  Expression() = default;
  ~Expression() = default;
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > operators = std::make_shared<std::vector<std::shared_ptr<Operator> > >();
  std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > sparsity = std::make_shared<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > >();

  void update_sparsity(std::shared_ptr<Node>, std::shared_ptr<Operator>);
  
  virtual std::sahred_ptr<std::vector<std::shared_ptr<Var> > > &get_vars() override;
  std::string __str__() override;

  double evaluate() override;
  double ad(Var& bool new_eval=true) override;
  double ad2(Var&, Var&, bool new_eval=true) override;
  bool has_ad(Var&) override;
  bool has_ad2(Var&, Var&) override;
  std::shared_ptr<ExpressionBase> sd(Var&, bool new_eval=true) override;
};
