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


const int ADD = -1;
const int SUBTRACT = -2;
const int MULTIPLY = -3;
const int DIVIDE = -4;
const int POWER = -5;


class Node;
class ExpressionBase;
class Leaf;
class Var;
class Param;
class Float;
class Expression;
class Operator;
class BinaryOperator;
class AddOperator;
class SubtractOperator;
class MultiplyOperator;
class DivideOperator;
class PowerOperator;


std::shared_ptr<Var> create_var(double value=0.0, double lb=-1.0e100, double ub=1.0e100, std::string name="");
std::shared_ptr<Param> create_param(double value=0.0, std::string name="");
std::shared_ptr<Float> create_float(double vlaue=0.0);


class Node
{
public:
  Node() = default;
  virtual ~Node() = default;
  double value;
  double der;
  virtual bool is_leaf();
  virtual bool is_var();
  virtual bool is_param();
  virtual bool is_float();
  virtual bool is_expr();
};


class ExpressionBase: public Node, public std::enable_shared_from_this<ExpressionBase>
{
public:
  ExpressionBase() = default;
  virtual ~ExpressionBase() = default;
  int index = -1;

  virtual std::shared_ptr<ExpressionBase> operator+(ExpressionBase&) = 0;
  virtual std::shared_ptr<ExpressionBase> operator-(ExpressionBase&) = 0;
  virtual std::shared_ptr<ExpressionBase> operator*(ExpressionBase&) = 0;
  virtual std::shared_ptr<ExpressionBase> operator/(ExpressionBase&) = 0;
  virtual std::shared_ptr<ExpressionBase> __pow__(ExpressionBase&) = 0;
  std::shared_ptr<ExpressionBase> operator-();
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

  virtual std::shared_ptr<std::vector<std::shared_ptr<Operator> > > get_operators();
  virtual std::shared_ptr<Expression> shallow_copy();
  virtual int get_num_operators();
  virtual std::string __str__() = 0;
  virtual double evaluate() = 0;
  virtual void rad(bool new_eval=true) = 0;
  virtual std::shared_ptr<Node> get_last_node();
  virtual std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars();
  virtual std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_leaves();
};


class Leaf: public ExpressionBase
{
public:
  Leaf() = default;
  virtual ~Leaf() = default;

  virtual std::shared_ptr<ExpressionBase> operator+(ExpressionBase&) override;
  virtual std::shared_ptr<ExpressionBase> operator-(ExpressionBase&) override;
  virtual std::shared_ptr<ExpressionBase> operator*(ExpressionBase&) override;
  virtual std::shared_ptr<ExpressionBase> operator/(ExpressionBase&) override;
  virtual std::shared_ptr<ExpressionBase> __pow__(ExpressionBase&) override;

  bool is_leaf() override;
  double evaluate() override;
  void rad(bool new_eval=true) override;
};


class Var: public Leaf
{
public:
  Var() = default;
  ~Var() = default;
  std::string name;
  double lb;
  double ub;

  bool is_var() override;
  std::string __str__() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() override;
};


class Float: public Leaf
{
public:
  Float() = default;
  ~Float() = default;

  std::shared_ptr<ExpressionBase> operator+(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator-(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator*(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator/(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> __pow__(ExpressionBase&) override;
  
  bool is_float() override;
  std::string __str__() override;
};


class Param: public Leaf
{
public:
  Param() = default;
  ~Param() = default;
  std::string name;

  std::string __str__() override;
  bool is_param() override;
};


class Expression: public ExpressionBase
{
public:
  Expression() = default;
  ~Expression() = default;
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > operators = std::make_shared<std::vector<std::shared_ptr<Operator> > >();
  int num_operators = 0;

  std::shared_ptr<ExpressionBase> operator+(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator-(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator*(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> operator/(ExpressionBase&) override;
  std::shared_ptr<ExpressionBase> __pow__(ExpressionBase&) override;
  
  std::shared_ptr<std::vector<std::shared_ptr<Operator> > > get_operators() override;
  std::shared_ptr<Expression> shallow_copy() override;
  int get_num_operators() override;
  bool is_expr() override;
  std::shared_ptr<Node> get_last_node() override;
  std::string __str__() override;
  void add_operator(std::shared_ptr<Operator>);
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_vars() override;
  std::shared_ptr<std::unordered_set<std::shared_ptr<ExpressionBase> > > get_leaves() override;

  double evaluate() override;
  void rad(bool new_eval=true) override;
};


class Operator: public Node
{
public:
  Operator() = default;
  Operator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): arg1(_arg1), arg2(_arg2) {}
  Operator(std::shared_ptr<Node> _arg1): arg1(_arg1) {}
  virtual ~Operator() = default;
  std::shared_ptr<Node> arg1;
  std::shared_ptr<Node> arg2;
  virtual void evaluate() = 0;
  virtual void rad() = 0;
  virtual std::shared_ptr<std::vector<std::shared_ptr<Node> > > get_args() = 0;
  virtual int get_operator_type() = 0;
  virtual bool is_unary() {return false;}
  virtual bool is_binary() {return false;}
};


class BinaryOperator: public Operator
{
public:
  BinaryOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): Operator(_arg1, _arg2) {}
  virtual ~BinaryOperator() = default;
  std::shared_ptr<std::vector<std::shared_ptr<Node> > > get_args() override;
  bool is_binary() override {return true;}
};


class AddOperator: public BinaryOperator
{
public:
  AddOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): BinaryOperator(_arg1, _arg2) {}
  void evaluate() override;
  void rad() override;
  int get_operator_type() override;
};


class SubtractOperator: public BinaryOperator
{
public:
  SubtractOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): BinaryOperator(_arg1, _arg2) {}
  void evaluate() override;
  void rad() override;
  int get_operator_type() override;
};


class MultiplyOperator: public BinaryOperator
{
public:
  MultiplyOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): BinaryOperator(_arg1, _arg2) {}
  void evaluate() override;
  void rad() override;
  int get_operator_type() override;
};


class DivideOperator: public BinaryOperator
{
public:
  DivideOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): BinaryOperator(_arg1, _arg2) {}
  void evaluate() override;
  void rad() override;
  int get_operator_type() override;
};


class PowerOperator: public BinaryOperator
{
public:
  PowerOperator(std::shared_ptr<Node> _arg1, std::shared_ptr<Node> _arg2): BinaryOperator(_arg1, _arg2) {}
  void evaluate() override;
  void rad() override;
  int get_operator_type() override;
};


