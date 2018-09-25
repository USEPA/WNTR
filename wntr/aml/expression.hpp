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


const short VALUE = 0;
const short ADD = 1;
const short SUBTRACT = 2;
const short MULTIPLY = 3;
const short DIVIDE = 4;
const short POWER = 5;


class ExpressionBase;
class Leaf;
class Var;
class Param;
class Float;
class Expression;


class ExpressionBase
{
public:
  ExpressionBase() = default;
  virtual ~ExpressionBase() = default;

  ExpressionBase* operator+(ExpressionBase&);
  ExpressionBase* operator-(ExpressionBase&);
  ExpressionBase* operator*(ExpressionBase&);
  ExpressionBase* operator/(ExpressionBase&);
  ExpressionBase* __pow__(ExpressionBase&);
  ExpressionBase* operator-();
  ExpressionBase* operator+(double);
  ExpressionBase* operator-(double);
  ExpressionBase* operator*(double);
  ExpressionBase* operator/(double);
  ExpressionBase* __pow__(double);
  ExpressionBase* __radd__(double);
  ExpressionBase* __rsub__(double);
  ExpressionBase* __rmul__(double);
  ExpressionBase* __rdiv__(double);
  ExpressionBase* __rtruediv__(double);
  ExpressionBase* __rpow__(double);

  virtual bool is_leaf();
  virtual bool is_var();
  virtual bool is_param();
  virtual bool is_float();
  virtual bool is_expr();
  virtual std::string __str__() = 0;
};


class Leaf: public ExpressionBase
{
public:
  Leaf() = default;
  Leaf(double val): value(val) {}
  virtual ~Leaf() = default;
  double value;

  bool is_leaf() override;
};


class Var: public Leaf
{
public:
  Var() = default;
  Var(double val): Leaf(val) {}
  ~Var() = default;
  std::string name;
  int index = -1;

  bool is_var() override;
  std::string __str__() override;
};


class Float: public Leaf
{
public:
  Float() = default;
  Float(double val): Leaf(val) {}
  ~Float() = default;
  int refcount = 0;

  bool is_float() override;
  std::string __str__() override;
};


class Param: public Leaf
{
public:
  Param() = default;
  Param(double val): Leaf(val) {}
  ~Param() = default;
  std::string name;

  std::string __str__() override;
  bool is_param() override;
};


class Expression: public ExpressionBase
{
public:
  Expression() = default;
  ~Expression();
  Expression(const Expression&) = delete;
  Expression &operator=(const Expression&) = delete;
  std::shared_ptr<std::vector<short> > operators = std::make_shared<std::vector<short> >();
  std::shared_ptr<std::vector<int> > args1 = std::make_shared<std::vector<int> >();
  std::shared_ptr<std::vector<int> > args2 = std::make_shared<std::vector<int> >();
  std::shared_ptr<std::vector<Leaf*> > leaves = std::make_shared<std::vector<Leaf*> >();
  std::shared_ptr<std::unordered_map<Leaf*, int> > leaf_to_ndx_map = std::make_shared<std::unordered_map<Leaf*, int> >();
  std::shared_ptr<std::vector<Float*> > floats = std::make_shared<std::vector<Float*> >();
  int num_operators = 0;
  int num_leaves = 0;
  int num_floats = 0;
  
  Expression* copy();
  bool is_expr() override;
  std::string __str__() override;
  void add_leaf(Leaf*);
};


int _arg_ndx_to_operator_ndx(int);
int _operator_ndx_to_arg_ndx(int);
