// To build wrapper:
//     swig -c++ -python -builtin aml_core.i
//     python setup.py build_ext --inplace

#include "expression.hpp"


std::unordered_set<std::shared_ptr<Var> > Node::py_get_vars()
{
  auto ptr_to_vars = get_vars();
  return *ptr_to_vars;
}


std::shared_ptr<Var> create_var(double value, double lb, double ub)
{
  std::shared_ptr<Var> v = std::make_shared<Var>();
  v->value = value;
  v->lb = lb;
  v->ub = ub;
  return v;
}


std::shared_ptr<Param> create_param(double value)
{
  std::shared_ptr<Param> p = std::make_shared<Param>();
  p->value = value;
  return p;
}


std::shared_ptr<Node> summation_helper(Node &n1, Node &n2, double c)
{
  if (n1.get_type() == "Summation")
    {
      auto nodes1 = n1.get_nodes();
      auto coefs1 = n1.get_coefs();
      auto sparsity1 = n1.get_sparsity();
      auto vars1 = n1.get_vars();
      
      if (n2.get_type() == "Summation")
	{
	  auto coefs2 = n2.get_coefs();
	  auto nodes2 = n2.get_nodes();
	  int i = 0;
	  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > _n_vars;
	  for (auto &_n : (*nodes2))
	    {
	      nodes1->push_back(_n);
	      coefs1->push_back(c*(*coefs2)[i]);
	      _n_vars = _n->get_vars();
	      for (auto &v : (*_n_vars))
		{
		  (*sparsity1)[v].push_back(nodes1->size()-1);
		  vars1->insert(v);
		}
	      ++i;
	    }
	  n1.add_const(c*n2.get_const());
	  return n1.shared_from_this();
	}
      else
	{
	  nodes1->push_back(n2.shared_from_this());
	  coefs1->push_back(c);
	  auto vars2 = n2.get_vars();
	  for (auto &v : (*vars2))
	    {
	      (*sparsity1)[v].push_back(nodes1->size()-1);
	      vars1->insert(v);
	    }
	  return n1.shared_from_this();
	}
    }
  else
    {
      if (n2.get_type() == "Summation")
	{
	  std::shared_ptr<std::vector<double> > new_coefs = std::make_shared<std::vector<double> >();
	  auto coefs2 = n2.get_coefs();
	  for (auto &_c : (*coefs2))
	    {
	      new_coefs->push_back(c*_c);
	    }
	  n2.multiply_const(c);
	  n2.set_coefs(new_coefs);
	  n2.get_nodes()->push_back(n1.shared_from_this());
	  n2.get_coefs()->push_back(1);
	  auto vars1 = n1.get_vars();
	  for (auto &v : (*vars1))
	    {
	      (*n2.get_sparsity())[v].push_back(n2.get_nodes()->size()-1);
	      n2.get_vars()->insert(v);
	    }
	  return n2.shared_from_this();
	}
      else
	{
	  std::shared_ptr<Summation> s = std::make_shared<Summation>();
	  s->get_nodes()->push_back(n1.shared_from_this());
	  s->get_coefs()->push_back(1);
	  s->get_nodes()->push_back(n2.shared_from_this());
	  s->get_coefs()->push_back(c);
	  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > n1_vars = n1.get_vars();
	  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > n2_vars = n2.get_vars();
	  for (auto &v : (*n1_vars))
	    {
	      (*(s->get_sparsity()))[v].push_back(0);
	      s->get_vars()->insert(v);
	    }
	  for (auto &v : (*n2_vars))
	    {
	      (*(s->get_sparsity()))[v].push_back(1);
	      s->get_vars()->insert(v);
	    }
	  return s;
	}
    }
}


std::shared_ptr<Node> Node::operator+(Node& n)
{
  return summation_helper(*this, n, 1);
}


std::shared_ptr<Node> Node::operator-(Node& n)
{
  return summation_helper(*this, n, -1);
}


std::shared_ptr<Node> Node::operator*(Node& n)
{
  if (get_type() == "Var")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<VarVarMultiplyOperator> oper = std::make_shared<VarVarMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<VarParamMultiplyOperator> oper = std::make_shared<VarParamMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<VarOperatorMultiplyOperator> oper = std::make_shared<VarOperatorMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<VarOperatorMultiplyOperator> oper = std::make_shared<VarOperatorMultiplyOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      n.get_vars()->insert(v1);
	    }
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Param")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<ParamVarMultiplyOperator> oper = std::make_shared<ParamVarMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<ParamParamMultiplyOperator> oper = std::make_shared<ParamParamMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<ParamOperatorMultiplyOperator> oper = std::make_shared<ParamOperatorMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<ParamOperatorMultiplyOperator> oper = std::make_shared<ParamOperatorMultiplyOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Summation")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarMultiplyOperator> oper = std::make_shared<OperatorVarMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamMultiplyOperator> oper = std::make_shared<OperatorParamMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorMultiplyOperator> oper = std::make_shared<OperatorOperatorMultiplyOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<OperatorOperatorMultiplyOperator> oper = std::make_shared<OperatorOperatorMultiplyOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      n.get_vars()->insert(v);
	    }
	  return n.shared_from_this();
	}
    }
  else
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarMultiplyOperator> oper = std::make_shared<OperatorVarMultiplyOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      get_vars()->insert(v2);
	    }
	  return shared_from_this();
	}
      if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamMultiplyOperator> oper = std::make_shared<OperatorParamMultiplyOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  return shared_from_this();
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorMultiplyOperator> oper = std::make_shared<OperatorOperatorMultiplyOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
      else
	{
	  std::shared_ptr<OperatorOperatorMultiplyOperator> oper = std::make_shared<OperatorOperatorMultiplyOperator>(get_nodes()->back()->shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  auto _n_nodes = n.get_nodes();
	  for (auto &_n : *(_n_nodes))
	    {
	      get_nodes()->push_back(_n);
	    }
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
    }
}


std::shared_ptr<Node> Node::operator/(Node& n)
{
  if (get_type() == "Var")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<VarVarDivideOperator> oper = std::make_shared<VarVarDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<VarParamDivideOperator> oper = std::make_shared<VarParamDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<VarOperatorDivideOperator> oper = std::make_shared<VarOperatorDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<VarOperatorDivideOperator> oper = std::make_shared<VarOperatorDivideOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      n.get_vars()->insert(v1);
	    }
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Param")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<ParamVarDivideOperator> oper = std::make_shared<ParamVarDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<ParamParamDivideOperator> oper = std::make_shared<ParamParamDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<ParamOperatorDivideOperator> oper = std::make_shared<ParamOperatorDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<ParamOperatorDivideOperator> oper = std::make_shared<ParamOperatorDivideOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Summation")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarDivideOperator> oper = std::make_shared<OperatorVarDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamDivideOperator> oper = std::make_shared<OperatorParamDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorDivideOperator> oper = std::make_shared<OperatorOperatorDivideOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<OperatorOperatorDivideOperator> oper = std::make_shared<OperatorOperatorDivideOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      n.get_vars()->insert(v);
	    }
	  return n.shared_from_this();
	}
    }
  else
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarDivideOperator> oper = std::make_shared<OperatorVarDivideOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      get_vars()->insert(v2);
	    }
	  return shared_from_this();
	}
      if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamDivideOperator> oper = std::make_shared<OperatorParamDivideOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  return shared_from_this();
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorDivideOperator> oper = std::make_shared<OperatorOperatorDivideOperator>(shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
      else
	{
	  std::shared_ptr<OperatorOperatorDivideOperator> oper = std::make_shared<OperatorOperatorDivideOperator>(get_nodes()->back()->shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  auto _n_nodes = n.get_nodes();
	  for (auto &_n : *(_n_nodes))
	    {
	      get_nodes()->push_back(_n);
	    }
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
    }
}


std::shared_ptr<Node> Node::__pow__(Node& n)
{
  if (get_type() == "Var")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<VarVarPowerOperator> oper = std::make_shared<VarVarPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<VarParamPowerOperator> oper = std::make_shared<VarParamPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : (*_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<VarOperatorPowerOperator> oper = std::make_shared<VarOperatorPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      expr->get_vars()->insert(v1);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<VarOperatorPowerOperator> oper = std::make_shared<VarOperatorPowerOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      n.get_vars()->insert(v1);
	    }
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Param")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<ParamVarPowerOperator> oper = std::make_shared<ParamVarPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<ParamParamPowerOperator> oper = std::make_shared<ParamParamPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(oper);
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<ParamOperatorPowerOperator> oper = std::make_shared<ParamOperatorPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<ParamOperatorPowerOperator> oper = std::make_shared<ParamOperatorPowerOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(oper);
	  return n.shared_from_this();
	}
    }
  else if (get_type() == "Summation")
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarPowerOperator> oper = std::make_shared<OperatorVarPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v2 : *(_n_vars))
	    {
	      expr->get_vars()->insert(v2);
	    }
	  return expr;
	}
      else if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamPowerOperator> oper = std::make_shared<OperatorParamPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorPowerOperator> oper = std::make_shared<OperatorOperatorPowerOperator>(shared_from_this(), n.shared_from_this());
	  std::shared_ptr<Expression> expr = std::make_shared<Expression>();
	  expr->get_nodes()->push_back(shared_from_this());
	  expr->get_nodes()->push_back(n.shared_from_this());
	  expr->get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  for (auto &v : *(_n_vars))
	    {
	      expr->get_vars()->insert(v);
	    }
	  return expr;
	}
      else
	{
	  std::shared_ptr<OperatorOperatorPowerOperator> oper = std::make_shared<OperatorOperatorPowerOperator>(shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  n.get_nodes()->push_back(shared_from_this());
	  n.get_nodes()->push_back(oper);
	  auto _vars = get_vars();
	  for (auto &v : *(_vars))
	    {
	      n.get_vars()->insert(v);
	    }
	  return n.shared_from_this();
	}
    }
  else
    {
      if (n.get_type() == "Var")
	{
	  std::shared_ptr<OperatorVarPowerOperator> oper = std::make_shared<OperatorVarPowerOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v2 : *(_n_vars))
	    {
	      get_vars()->insert(v2);
	    }
	  return shared_from_this();
	}
      if (n.get_type() == "Param")
	{
	  std::shared_ptr<OperatorParamPowerOperator> oper = std::make_shared<OperatorParamPowerOperator>(get_nodes()->back()->shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(oper);
	  return shared_from_this();
	}
      else if (n.get_type() == "Summation")
	{
	  std::shared_ptr<OperatorOperatorPowerOperator> oper = std::make_shared<OperatorOperatorPowerOperator>(shared_from_this(), n.shared_from_this());
	  get_nodes()->push_back(n.shared_from_this());
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
      else
	{
	  std::shared_ptr<OperatorOperatorPowerOperator> oper = std::make_shared<OperatorOperatorPowerOperator>(get_nodes()->back()->shared_from_this(), n.get_nodes()->back()->shared_from_this());
	  auto _n_nodes = n.get_nodes();
	  for (auto &_n : *(_n_nodes))
	    {
	      get_nodes()->push_back(_n);
	    }
	  get_nodes()->push_back(oper);
	  auto _n_vars = n.get_vars();
	  for (auto &v : *(_n_vars))
	    {
	      get_vars()->insert(v);
	    }
	  return shared_from_this();
	}
    }
}


std::shared_ptr<Node> Node::operator-()
{
  if (get_type() == "Var")
    {
      std::shared_ptr<Summation> s = std::make_shared<Summation>();
      s->get_nodes()->push_back(shared_from_this());
      s->get_coefs()->push_back(-1);
      auto _vars = get_vars();
      for (auto &v1 : *(_vars))
	{
	  s->get_vars()->insert(v1);
	  (*(s->get_sparsity()))[v1].push_back(0);
	}
      return s->shared_from_this();
    }
  else if (get_type() == "Param")
    {
      std::shared_ptr<Summation> s = std::make_shared<Summation>();
      s->get_nodes()->push_back(shared_from_this());
      s->get_coefs()->push_back(-1);
      return s->shared_from_this();
    }
  if (get_type() == "Summation")
    {
      std::shared_ptr<std::vector<double> > new_coefs = std::make_shared<std::vector<double> >();
      auto _coefs = get_coefs();
      for (auto &_c : *(_coefs))
	{
	  new_coefs->push_back(-_c);
	}
      set_coefs(new_coefs);
      multiply_const(-1);
      return shared_from_this();
    }
  else
    {
      std::shared_ptr<Summation> s = std::make_shared<Summation>();
      s->get_nodes()->push_back(shared_from_this());
      s->get_coefs()->push_back(-1);
      auto _vars = get_vars();
      for (auto &v : *(_vars))
	{
	  s->get_vars()->insert(v);
	  (*(s->get_sparsity()))[v].push_back(0);
	}
      return s->shared_from_this();
    }
}


std::shared_ptr<Node> Node::operator+(double c)
{
  return add_const(c);
}


std::shared_ptr<Node> Node::operator-(double c)
{
  return add_const(-c);
}


std::shared_ptr<Node> Node::add_const(double c)
{
  std::shared_ptr<Summation> s = std::make_shared<Summation>();
  s->add_const(c);
  s->nodes->push_back(shared_from_this());
  s->coefs->push_back(1);
  if (get_type() == "Var")
    {
      auto _vars = get_vars();
      for (auto &v1 : *(_vars))
	{
	  s->vars->insert(v1);
	  (*(s->sparsity))[v1].push_back(0);
	}
    }
  else if (get_type() == "Expression")
    {
      auto _vars = get_vars();
      for (auto &v : (*_vars))
	{
	  s->vars->insert(v);
	  (*(s->sparsity))[v].push_back(0);
	}
    }
  return s;
}


std::shared_ptr<Node> Summation::add_const(double c)
{
  constant += c;
  return shared_from_this();
}


void Node::multiply_const(double c)
{
  return;
}


void Summation::multiply_const(double c)
{
  constant *= c;
}


double Node::get_const()
{
  return 0.0;
}


double Summation::get_const()
{
  return constant;
}


std::shared_ptr<Node> Node::operator*(double c)
{
  if (get_type() == "Summation")
    {
      multiply_const(c);
      auto coefs = get_coefs();
      int coefs_size = coefs->size();
      for (int i=0; i < coefs_size; ++i)
	{
	  (*coefs)[i] = c * (*coefs)[i];
	}
      return shared_from_this();
    }
  else
    {
      std::shared_ptr<Summation> s = std::make_shared<Summation>();
      s->nodes->push_back(shared_from_this());
      s->coefs->push_back(c);
      if (get_type() == "Var")
	{
	  auto _vars = get_vars();
	  for (auto &v1 : *(_vars))
	    {
	      s->vars->insert(v1);
	      (*(s->sparsity))[v1].push_back(0);
	    }
	}
      else if (get_type() == "Expression")
	{
	  auto _vars = get_vars();
	  for (auto &v : (*_vars))
	    {
	      s->vars->insert(v);
	      (*(s->sparsity))[v].push_back(0);
	    }
	}
      return s;
    }
}


std::shared_ptr<Node> Node::operator/(double c)
{
  return (*this) * (1.0/c);
}


std::shared_ptr<Node> Node::__pow__(double c)
{
  std::shared_ptr<Param> p = std::make_shared<Param>();
  p->value = c;
  return this->__pow__(*p);
}


std::shared_ptr<Node> Node::__radd__(double c)
{
  return (*this) + c;
}


std::shared_ptr<Node> Node::__rsub__(double c)
{
  return (*(-(*this))) + c;
}


std::shared_ptr<Node> Node::__rmul__(double c)
{
  return (*this) * c;
}


std::shared_ptr<Node> Node::__rdiv__(double c)
{
  return __rtruediv__(c);
}


std::shared_ptr<Node> Node::__rtruediv__(double c)
{
  std::shared_ptr<Param> p = std::make_shared<Param>();
  p->value = c;
  return (*p)/(*this);
}


std::shared_ptr<Node> Node::__rpow__(double c)
{
  std::shared_ptr<Param> p = std::make_shared<Param>();
  p->value = c;
  return p->__pow__(*this);
}


std::shared_ptr<std::vector<std::shared_ptr<Node> > > Node::get_nodes()
{
  return std::make_shared<std::vector<std::shared_ptr<Node> > >();
}


std::shared_ptr<std::vector<std::shared_ptr<Node> > > Summation::get_nodes()
{
  return nodes;
}


std::shared_ptr<std::vector<std::shared_ptr<Node> > > Expression::get_nodes()
{
  return nodes;
}


std::shared_ptr<std::vector<double> > Node::get_coefs()
{
  return std::make_shared<std::vector<double> >();
}


std::shared_ptr<std::vector<double> > Summation::get_coefs()
{
  return coefs;
}


void Node::set_coefs(std::shared_ptr<std::vector<double> > new_coefs)
{
  return;
}


void Summation::set_coefs(std::shared_ptr<std::vector<double> > new_coefs)
{
  coefs = new_coefs;
}


std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > Node::get_sparsity()
{
  return std::make_shared<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > >();
}


std::shared_ptr<std::unordered_map<std::shared_ptr<Node>, std::vector<int> > > Summation::get_sparsity()
{
  return sparsity;
}


std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > Node::get_vars()
{
  return std::make_shared<std::unordered_set<std::shared_ptr<Var> > >();
}


std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > Summation::get_vars()
{
  return vars;
}


std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > Var::get_vars()
{
  std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > vars = std::make_shared<std::unordered_set<std::shared_ptr<Var> > >();
  vars->insert(std::static_pointer_cast<Var>(shared_from_this()));
  return vars;
}


std::shared_ptr<std::unordered_set<std::shared_ptr<Var> > > Expression::get_vars()
{
  return vars;
}


std::string Node::get_type()
{
  return "Node";
}


std::string Summation::get_type()
{
  return "Summation";
}


std::string Var::get_type()
{
  return "Var";
}


std::string Param::get_type()
{
  return "Param";
}


std::string Expression::get_type()
{
  return "Expression";
}


double Summation::evaluate()
{
  value = constant;
  int i = 0;
  for (auto &n : *nodes)
  {
    value += (*coefs)[i] * n->evaluate();
    i++;
  }
  return value;
}


double Summation::ad(Var &n, bool new_eval)
{
  if (new_eval)
    {
      evaluate();
    }
  der_n1 = 0;
  for (int &ndx : (*sparsity)[n.shared_from_this()])
  {
    der_n1 += (*coefs)[ndx] * (*nodes)[ndx]->ad(n, new_eval);
  }
  return der_n1;
}


double Summation::ad2(Var &n1, Var &n2, bool new_eval)
{
  if (new_eval)
    {
      evaluate();
    }
  der_n1 = 0;
  for (int &ndx : (*sparsity)[n1.shared_from_this()])
    {
      der_n1 += (*coefs)[ndx] * (*nodes)[ndx]->ad(n1, new_eval);
    }
  der_n2 = 0;
  for (int &ndx : (*sparsity)[n2.shared_from_this()])
    {
      der_n2 += (*coefs)[ndx] * (*nodes)[ndx]->ad(n2, new_eval);
    }
  der2 = 0;
  for (int &ndx : (*sparsity)[n1.shared_from_this()])
  {
    der2 += (*coefs)[ndx] * (*nodes)[ndx]->ad2(n1, n2, new_eval);
  }
  return der2;
}


double Var::evaluate()
{
  return value;
}


double Param::evaluate()
{
  return value;
}


double VarVarMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double VarParamMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double VarOperatorMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double ParamVarMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double ParamParamMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double ParamOperatorMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double OperatorVarMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double OperatorParamMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double OperatorOperatorMultiplyOperator::evaluate()
{
  value = (*node1).value * (*node2).value;
  return value;
}


double VarVarDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double VarParamDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double VarOperatorDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double ParamVarDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double ParamParamDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double ParamOperatorDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double OperatorVarDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double OperatorParamDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double OperatorOperatorDivideOperator::evaluate()
{
  value = (*node1).value / (*node2).value;
  return value;
}


double VarVarPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double VarParamPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double VarOperatorPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double ParamVarPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double ParamParamPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double ParamOperatorPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double OperatorVarPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double OperatorParamPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double OperatorOperatorPowerOperator::evaluate()
{
  value = ::pow((*node1).value, (*node2).value);
  return value;
}


double Var::ad(Var &n, bool new_eval)
{
  if (this == &n)
  {
      return 1.0;
  }
  else
  {
      return 0.0;
  }
}


double Param::ad(Var &n, bool new_eval)
{
  return 0.0;
}


double VarVarMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).ad(n, new_eval) + (*node2).value * (*node1).ad(n, new_eval);
  return der_n1;
}


double VarParamMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node2).value * (*node1).ad(n, new_eval);
  return der_n1;
}


double VarOperatorMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).der_n1 + (*node2).value * (*node1).ad(n, new_eval);
  return der_n1;
}


double ParamVarMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).ad(n, new_eval);
  return der_n1;
}


double ParamParamMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = 0.0;
  return der_n1;
}


double ParamOperatorMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).der_n1;
  return der_n1;
}


double OperatorVarMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).ad(n, new_eval) + (*node2).value * (*node1).der_n1;
  return der_n1;
}


double OperatorParamMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node2).value * (*node1).der_n1;
  return der_n1;
}


double OperatorOperatorMultiplyOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).value * (*node2).der_n1 + (*node2).value * (*node1).der_n1;
  return der_n1;
}


double VarVarDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ((*node2).value * (*node1).ad(n, new_eval) - (*node1).value * (*node2).ad(n, new_eval)) / ((*node2).value * (*node2).value);
  return der_n1;
}


double VarParamDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).ad(n, new_eval) / (*node2).value;
  return der_n1;
}


double VarOperatorDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ((*node2).value * (*node1).ad(n, new_eval) - (*node1).value * (*node2).der_n1) / ((*node2).value * (*node2).value);
  return der_n1;
}


double ParamVarDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ( - (*node1).value * (*node2).ad(n, new_eval)) / ((*node2).value * (*node2).value);
  return der_n1;
}


double ParamParamDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = 0.0;
  return der_n1;
}


double ParamOperatorDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ( - (*node1).value * (*node2).der_n1) / ((*node2).value * (*node2).value);
  return der_n1;
}


double OperatorVarDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ((*node2).value * (*node1).der_n1 - (*node1).value * (*node2).ad(n, new_eval)) / ((*node2).value * (*node2).value);
  return der_n1;
}


double OperatorParamDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node1).der_n1 / (*node2).value;
  return der_n1;
}


double OperatorOperatorDivideOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ((*node2).value * (*node1).der_n1 - (*node1).value * (*node2).der_n1) / ((*node2).value * (*node2).value);
  return der_n1;
}


double VarVarPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * ((*node2).value * (*node1).ad(n, new_eval) * (1.0 / (*node1).value) + (*node2).ad(n, new_eval) * log((*node1).value));
  return der_n1;
}


double VarParamPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node2).value * ::pow((*node1).value, ((*node2).value - 1.0)) * (*node1).ad(n, new_eval);
  return der_n1;
}


double VarOperatorPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * ((*node2).value * (*node1).ad(n, new_eval) * (1.0 / (*node1).value) + (*node2).der_n1 * log((*node1).value));
  return der_n1;
}


double ParamVarPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * (*node2).ad(n, new_eval) * log((*node1).value);
  return der_n1;
}


double ParamParamPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = 0.0;
  return der_n1;
}


double ParamOperatorPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * (*node2).der_n1 * log((*node1).value);
  return der_n1;
}


double OperatorVarPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * ((*node2).value * (*node1).der_n1 * (1.0 / (*node1).value) + (*node2).ad(n, new_eval) * log((*node1).value));
  return der_n1;
}


double OperatorParamPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = (*node2).value * ::pow((*node1).value, ((*node2).value - 1.0)) * (*node1).der_n1;
  return der_n1;
}


double OperatorOperatorPowerOperator::ad(Var &n, bool new_eval)
{
  der_n1 = ::pow((*node1).value, (*node2).value) * ((*node2).value * (*node1).der_n1 * (1.0 / (*node1).value) + (*node2).der_n1 * log((*node1).value));
  return der_n1;
}


double Var::ad2(Var &n1, Var &n2, bool new_eval)
{
  return 0.0;
}


double Param::ad2(Var &n1, Var &n2, bool new_eval)
{
  return 0.0;
}


double VarVarMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = node1->ad(n1, new_eval);
  double node1_der_n2 = node1->ad(n2, new_eval);
  double node2_der_n1 = node2->ad(n1, new_eval);
  double node2_der_n2 = node2->ad(n2, new_eval);
  der_n1 = node1->value * node2_der_n1 + node2->value * node1_der_n1;
  der_n2 = node1->value * node2_der_n2 + node2->value * node1_der_n2;
  der2 = node1_der_n1 * node2_der_n2 + node2_der_n1 * node1_der_n2;
  return der2;
}


double VarParamMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = node1->ad(n1, new_eval);
  double node1_der_n2 = node1->ad(n2, new_eval);
  der_n1 = node2->value * node1_der_n1;
  der_n2 = node2->value * node1_der_n2;
  der2 = 0.0;
  return der2;
}


double VarOperatorMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = node1->ad(n1, new_eval);
  double node1_der_n2 = node1->ad(n2, new_eval);
  der_n1 = node1->value * node2->der_n1 + node2->value * node1_der_n1;
  der_n2 = node1->value * node2->der_n2 + node2->value * node1_der_n2;
  der2 = (node1->value * node2->der2 +
          node2->der_n1 * node1_der_n2 +
          node2->der_n2 * node1_der_n1);
  return der2;
}


double ParamVarMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = node2->ad(n1, new_eval);
  double node2_der_n2 = node2->ad(n2, new_eval);
  der_n1 = node1->value * node2_der_n1;
  der_n2 = node1->value * node2_der_n2;
  der2 = 0.0;
  return der2;
}


double ParamParamMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = 0.0;
  der_n2 = 0.0;
  der2 = 0.0;
  return der2;
}


double ParamOperatorMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = node1->value * node2->der_n1;
  der_n2 = node1->value * node2->der_n2;
  der2 = (node1->value * node2->der2);
  return der2;
}


double OperatorVarMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = node2->ad(n1, new_eval);
  double node2_der_n2 = node2->ad(n2, new_eval);
  der_n1 = node2->value * node1->der_n1 + node1->value * node2_der_n1;
  der_n2 = node2->value * node1->der_n2 + node1->value * node2_der_n2;
  der2 = (node2->value * node1->der2 +
          node1->der_n1 * node2_der_n2 +
          node1->der_n2 * node2_der_n1);
  return der2;
}


double OperatorParamMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = node2->value * node1->der_n1;
  der_n2 = node2->value * node1->der_n2;
  der2 = (node2->value * node1->der2);
  return der2;
}


double OperatorOperatorMultiplyOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = node1->value * node2->der_n1 + node2->value * node1->der_n1;
  der_n2 = node1->value * node2->der_n2 + node2->value * node1->der_n2;
  der2 = (node1->value * node2->der2 + node2->der_n1 * node1->der_n2 +
          node2->value * node1->der2 + node1->der_n1 * node2->der_n2);
  return der2;
}


double VarVarDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);

  der_n1 = (node2->value * node1_der_n1 - node1->value * node2_der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1_der_n2 - node1->value * node2_der_n2) / (node2->value * node2->value);
  der2 = (-node2->value*node1_der_n1*node2_der_n2 -
          node2->value*node2_der_n1*node1_der_n2 +
          2.0*node1->value*node2_der_n1*node2_der_n2) / ::pow(node2->value, 3);
  return der2;
}


double VarParamDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);

  der_n1 = (node2->value * node1_der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1_der_n2) / (node2->value * node2->value);
  der2 = 0.0;
  return der2;
}


double VarOperatorDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);

  der_n1 = (node2->value * node1_der_n1 - node1->value * node2->der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1_der_n2 - node1->value * node2->der_n2) / (node2->value * node2->value);
  der2 = (-node2->value*node1_der_n1*node2->der_n2 - node1->value*node2->value*node2->der2 -
          node2->value*node2->der_n1*node1_der_n2 + 2.0*node1->value*node2->der_n1*node2->der_n2) / ::pow(node2->value, 3);
  return der2;
}


double ParamVarDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);

  der_n1 = (-node1->value * node2_der_n1) / (node2->value * node2->value);
  der_n2 = (-node1->value * node2_der_n2) / (node2->value * node2->value);
  der2 = (2.0*node1->value*node2_der_n1*node2_der_n2) / ::pow(node2->value, 3);
  return der2;
}


double ParamParamDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = 0.0;
  der_n2 = 0.0;
  der2 = 0.0;
  return der2;
}


double ParamOperatorDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = (-node1->value * node2->der_n1) / (node2->value * node2->value);
  der_n2 = (-node1->value * node2->der_n2) / (node2->value * node2->value);
  der2 = (-node1->value*node2->value*node2->der2 + 2.0*node1->value*node2->der_n1*node2->der_n2) / ::pow(node2->value, 3);
  return der2;
}


double OperatorVarDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);

  der_n1 = (node2->value * node1->der_n1 - node1->value * node2_der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1->der_n2 - node1->value * node2_der_n2) / (node2->value * node2->value);
  der2 = (node2->value*node2->value*node1->der2 -
          node2->value*node1->der_n1*node2_der_n2 -
          node2->value*node2_der_n1*node1->der_n2 +
          2.0*node1->value*node2_der_n1*node2_der_n2) / ::pow(node2->value, 3);
  return der2;
}


double OperatorParamDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = (node2->value * node1->der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1->der_n2) / (node2->value * node2->value);
  der2 = (node2->value*node2->value*node1->der2) / ::pow(node2->value, 3);
  return der2;
}


double OperatorOperatorDivideOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = (node2->value * node1->der_n1 - node1->value * node2->der_n1) / (node2->value * node2->value);
  der_n2 = (node2->value * node1->der_n2 - node1->value * node2->der_n2) / (node2->value * node2->value);
  der2 = (node2->value*node2->value*node1->der2 -
          node2->value*node1->der_n1*node2->der_n2 -
          node1->value*node2->value*node2->der2 -
          node2->value*node2->der_n1*node1->der_n2 +
          2.0*node1->value*node2->der_n1*node2->der_n2) / ::pow(node2->value, 3);
  return der2;
}


double VarVarPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);
  double log_node1 = log(node1->value);

  der_n1 = value * (node2->value * node1_der_n1 * (1.0 / node1->value) + node2_der_n1 * log_node1);
  der_n2 = value * (node2->value * node1_der_n2 * (1.0 / node1->value) + node2_der_n2 * log_node1);
  der2 = ::pow(node1->value, (node2->value-2.0)) * (node1->value * (1 + node2->value * log_node1) * node1_der_n1 * node2_der_n2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1_der_n2 * node2_der_n1 +
                                                  (node2->value * node2->value - node2->value) * node1_der_n1 * node1_der_n2 +
                                                  ::pow((node1->value * log_node1), 2.0) * node2_der_n1 * node2_der_n2);
  return der2;
}


double VarParamPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);

  der_n1 = node2->value * ::pow(node1->value, (node2->value - 1.0)) * node1_der_n1;
  der_n2 = node2->value * ::pow(node1->value, (node2->value - 1.0)) * node1_der_n2;
  der2 = ::pow(node1->value, (node2->value-2.0)) * ((node2->value * node2->value - node2->value) * node1_der_n1 * node1_der_n2);
  return der2;
}


double VarOperatorPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node1_der_n1 = (*node1).ad(n1, new_eval);
  double node1_der_n2 = (*node1).ad(n2, new_eval);
  double log_node1 = log(node1->value);

  der_n1 = (::pow(node1->value, node2->value) * (node2->value * node1_der_n1 * (1.0 / node1->value) + node2->der_n1 * log_node1));
  der_n2 = (::pow(node1->value, node2->value) * (node2->value * node1_der_n2 * (1.0 / node1->value) + node2->der_n2 * log_node1));
  der2 = ::pow(node1->value, (node2->value-2.0)) * (node1->value * node1->value * log_node1 * node2->der2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1_der_n1 * node2->der_n2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1_der_n2 * node2->der_n1 +
                                                  (node2->value * node2->value - node2->value) * node1_der_n1 * node1_der_n2 +
                                                  ::pow((node1->value * log_node1), 2.0) * node2->der_n1 * node2->der_n2);
  return der2;
}


double ParamVarPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);
  double log_node1 = log(node1->value);

  der_n1 = value * node2_der_n1 * log_node1;
  der_n2 = value * node2_der_n2 * log_node1;
  der2 = value * log_node1 * log_node1 * node2_der_n1 * node2_der_n2;
  return der2;
}


double ParamParamPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = 0.0;
  der_n2 = 0.0;
  der2 = 0.0;
  return der2;
}


double ParamOperatorPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double log_node1 = log(node1->value);

  der_n1 = value * node2->der_n1 * log_node1;
  der_n2 = value * node2->der_n2 * log_node1;
  der2 = value * log_node1 * (node2->der2 +
                              log_node1 * node2->der_n1 * node2->der_n2);
  return der2;
}


double OperatorVarPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double node2_der_n1 = (*node2).ad(n1, new_eval);
  double node2_der_n2 = (*node2).ad(n2, new_eval);
  double log_node1 = log(node1->value);

  der_n1 = value * (node2->value * node1->der_n1 * (1.0 / node1->value) + node2_der_n1 * log_node1);
  der_n2 = value * (node2->value * node1->der_n2 * (1.0 / node1->value) + node2_der_n2 * log_node1);
  der2 = ::pow(node1->value, (node2->value-2.0)) * (node1->value * node2->value * node1->der2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1->der_n1 * node2_der_n2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1->der_n2 * node2_der_n1 +
                                                  (node2->value * node2->value - node2->value) * node1->der_n1 * node1->der_n2 +
                                                  ::pow((node1->value * log_node1), 2.0) * node2_der_n1 * node2_der_n2);
  return der2;
}


double OperatorParamPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  der_n1 = node2->value * ::pow(node1->value, (node2->value - 1.0)) * node1->der_n1;
  der_n2 = node2->value * ::pow(node1->value, (node2->value - 1.0)) * node1->der_n2;
  der2 = ::pow(node1->value, (node2->value-2.0)) * node2->value * (node1->value * node1->der2 +
                                                                 (node2->value - 1.0) * node1->der_n1 * node1->der_n2);
  return der2;
}


double OperatorOperatorPowerOperator::ad2(Var &n1, Var &n2, bool new_eval)
{
  double log_node1 = log(node1->value);

  der_n1 = value * (node2->value * node1->der_n1 * (1.0 / node1->value) + node2->der_n1 * log_node1);
  der_n2 = value * (node2->value * node1->der_n2 * (1.0 / node1->value) + node2->der_n2 * log_node1);
  der2 = ::pow(node1->value, (node2->value-2.0)) * (node1->value * node2->value * node1->der2 +
                                                  node1->value * node1->value * log_node1 * node2->der2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1->der_n1 * node2->der_n2 +
                                                  node1->value * (1 + node2->value * log_node1) * node1->der_n2 * node2->der_n1 +
                                                  (node2->value * node2->value - node2->value) * node1->der_n1 * node1->der_n2 +
                                                  ::pow((node1->value * log_node1), 2.0) * node2->der_n1 * node2->der_n2);
  return der2;
}


bool Node::has_ad(Var &n)
{
  if (this == &n)
  {
      return true;
  }
  else
  {
      return false;
  }
}


bool Summation::has_ad(Var &n)
{
  has_der_n1 = 0;
  for (int &ndx : (*sparsity)[n.shared_from_this()])
    {
      has_der_n1 += (*nodes)[ndx]->has_ad(n);
    }
  return has_der_n1;
}


bool Expression::has_ad(Var &n)
{
  for (auto &_n : (*nodes))
    {
      _n->has_ad(n);
    }
  has_der_n1 = nodes->back()->has_der_n1;
  return has_der_n1;
}


bool Var::has_ad2(Var &n1, Var &n2)
{
  return false;
}


bool Param::has_ad2(Var &n1, Var &n2)
{
  return false;
}


bool Summation::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = 0;
  has_der_n2 = 0;
  has_der2 = 0;
  for (int &ndx : (*sparsity)[n1.shared_from_this()])
    {
      has_der_n1 += (*nodes)[ndx]->has_ad(n1);
    }
  for (int &ndx : (*sparsity)[n2.shared_from_this()])
    {
      has_der_n2 += (*nodes)[ndx]->has_ad(n2);
    }
  for (int &ndx : (*sparsity)[n1.shared_from_this()])
    {
      has_der2 += (*nodes)[ndx]->has_ad2(n1, n2);
    }
  return has_der2;
}


bool VarVarMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_ad(n1);
  has_der_n2 = node1->has_ad(n2) + node2->has_ad(n2);
  has_der2 = node1->has_ad(n2)*node2->has_ad(n1) + node1->has_ad(n1)*node2->has_ad(n2);
  return has_der2;
}


bool VarParamMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1);
  has_der_n2 = node1->has_ad(n2);
  has_der2 = false;
  return has_der2;
}


bool VarOperatorMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_der_n1;
  has_der_n2 = node1->has_ad(n2) + node2->has_der_n2;
  has_der2 = node2->has_der2 + node1->has_ad(n2)*node2->has_der_n1 + node1->has_ad(n1)*node2->has_der_n2;
  return has_der2;
}


bool ParamVarMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_ad(n1);
  has_der_n2 = node2->has_ad(n2);
  has_der2 = false;
  return has_der2;
}


bool ParamParamMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = false;
  has_der_n2 = false;
  has_der2 = false;
  return has_der2;
}


bool ParamOperatorMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_der_n1;
  has_der_n2 = node2->has_der_n2;
  has_der2 = node2->has_der2;
  return has_der2;
}


bool OperatorVarMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_ad(n1);
  has_der_n2 = node1->has_der_n2 + node2->has_ad(n2);
  has_der2 = node1->has_der_n2*node2->has_ad(n1) + node1->has_der2 + node1->has_der_n1*node2->has_ad(n2);
  return has_der2;
}


bool OperatorParamMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1;
  has_der_n2 = node1->has_der_n2;
  has_der2 = node1->has_der2;
  return has_der2;
}


bool OperatorOperatorMultiplyOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_der_n1;
  has_der_n2 = node1->has_der_n2 + node2->has_der_n2;
  has_der2 = node2->has_der2 + node1->has_der_n2*node2->has_der_n1 + node1->has_der2 + node1->has_der_n1*node2->has_der_n2;
  return has_der2;
}


bool VarVarDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_ad(n1);
  has_der_n2 = node1->has_ad(n2) + node2->has_ad(n2);
  has_der2 = (node1->has_ad(n1)*node2->has_ad(n2) +
              node2->has_ad(n1)*node1->has_ad(n2) +
              node2->has_ad(n1)*node2->has_ad(n2));
  return has_der2;
}


bool VarParamDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1);
  has_der_n2 = node1->has_ad(n2);
  has_der2 = false;
  return has_der2;
}


bool VarOperatorDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_der_n1;
  has_der_n2 = node1->has_ad(n2) + node2->has_der_n2;
  has_der2 = (node1->has_ad(n1)*node2->has_der_n2 +
              node2->has_der2 + node2->has_der_n1*node1->has_ad(n2) +
              node2->has_der_n1*node2->has_der_n2);
  return has_der2;
}


bool ParamVarDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_ad(n1);
  has_der_n2 = node2->has_ad(n2);
  has_der2 = node2->has_ad(n1)*node2->has_ad(n2);
  return has_der2;
}


bool ParamParamDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = false;
  has_der_n2 = false;
  has_der2 = false;
  return has_der2;
}


bool ParamOperatorDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_der_n1;
  has_der_n2 = node2->has_der_n2;
  has_der2 = node2->has_der2 + node2->has_der_n1*node2->has_der_n2;
  return has_der2;
}


bool OperatorVarDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_ad(n1);
  has_der_n2 = node1->has_der_n2 + node2->has_ad(n2);
  has_der2 = (node1->has_der2 + node1->has_der_n1*node2->has_ad(n2) +
              node2->has_ad(n1)*node1->has_der_n2 +
              node2->has_ad(n1)*node2->has_ad(n2));
  return has_der2;
}


bool OperatorParamDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1;
  has_der_n2 = node1->has_der_n2;
  has_der2 = node1->has_der2;
  return has_der2;
}


bool OperatorOperatorDivideOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_der_n1;
  has_der_n2 = node1->has_der_n2 + node2->has_der_n2;
  has_der2 = (node1->has_der2 + node1->has_der_n1*node2->has_der_n2 +
              node2->has_der2 + node2->has_der_n1*node1->has_der_n2 +
              node2->has_der_n1*node2->has_der_n2);
  return has_der2;
}


bool VarVarPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_ad(n1);
  has_der_n2 = node1->has_ad(n2) + node2->has_ad(n2);
  has_der2 = (node1->has_ad(n1) * node2->has_ad(n2) +
              node1->has_ad(n2) * node2->has_ad(n1) + node1->has_ad(n1) * node1->has_ad(n2) +
              node2->has_ad(n1) * node2->has_ad(n2));
  return has_der2;
}


bool VarParamPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1);
  has_der_n2 = node1->has_ad(n2);
  has_der2 = node1->has_ad(n1) * node1->has_ad(n2);
  return has_der2;
}


bool VarOperatorPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_ad(n1) + node2->has_der_n1;
  has_der_n2 = node1->has_ad(n2) + node2->has_der_n2;
  has_der2 = (node2->has_der2 + node1->has_ad(n1) * node2->has_der_n2 +
              node1->has_ad(n2) * node2->has_der_n1 + node1->has_ad(n1) * node1->has_ad(n2) +
              node2->has_der_n1 * node2->has_der_n2);
  return has_der2;
}


bool ParamVarPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_ad(n1);
  has_der_n2 = node2->has_ad(n2);
  has_der2 = node2->has_ad(n1) * node2->has_ad(n2);
  return has_der2;
}


bool ParamParamPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = false;
  has_der_n2 = false;
  has_der2 = false;
  return has_der2;
}


bool ParamOperatorPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node2->has_der_n1;
  has_der_n2 = node2->has_der_n2;
  has_der2 = node2->has_der2 + node2->has_der_n1 * node2->has_der_n2;
  return has_der2;
}


bool OperatorVarPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_ad(n1);
  has_der_n2 = node1->has_der_n2 + node2->has_ad(n2);
  has_der2 = (node1->has_der2 + node1->has_der_n1 * node2->has_ad(n2) +
              node1->has_der_n2 * node2->has_ad(n1) + node1->has_der_n1 * node1->has_der_n2 +
              node2->has_ad(n1) * node2->has_ad(n2));
  return has_der2;
}


bool OperatorParamPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1;
  has_der_n2 = node1->has_der_n2;
  has_der2 = node1->has_der2 + node1->has_der_n1 * node1->has_der_n2;
  return has_der2;
}


bool OperatorOperatorPowerOperator::has_ad2(Var &n1, Var &n2)
{
  has_der_n1 = node1->has_der_n1 + node2->has_der_n1;
  has_der_n2 = node1->has_der_n2 + node2->has_der_n2;
  has_der2 = (node1->has_der2 + node2->has_der2 + node1->has_der_n1 * node2->has_der_n2 +
              node1->has_der_n2 * node2->has_der_n1 + node1->has_der_n1 * node1->has_der_n2 +
              node2->has_der_n1 * node2->has_der_n2);
  return has_der2;
}


std::string Var::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return name;
}


std::string Param::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  if (name == "")
    {
      std::ostringstream s;
      s << value;
      return s.str();
    }
  else
    {
      return name;
    }
}


std::string Summation::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  std::string s = "(";
  std::ostringstream c;
  c << constant;
  s += c.str();
  int i = 0;
  for (auto &n : (*nodes))
    {
      s += " + ";
      std::ostringstream c;
      c << (*coefs)[i];
      s += c.str();
      s += "*";
      s += n->set_name(str_map);
      ++i;
    }
  s += ")";
  return s;
}


std::string Expression::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  std::string res;
  for (auto &n : (*nodes))
  {
      res = n->set_name(str_map);
      str_map[n] = res;
  }
  return str_map[nodes->back()];
}


std::string VarVarMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + node2->set_name(str_map) + ")";
}


std::string VarParamMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + node2->set_name(str_map) + ")";
}


std::string VarOperatorMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + str_map[node2] + ")";
}


std::string ParamVarMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + node2->set_name(str_map) + ")";
}


std::string ParamParamMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + node2->set_name(str_map) + ")";
}


std::string ParamOperatorMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " * " + str_map[node2] + ")";
}


std::string OperatorVarMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " * " + node2->set_name(str_map) + ")";
}


std::string OperatorParamMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " * " + node2->set_name(str_map) + ")";
}


std::string OperatorOperatorMultiplyOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " * " + str_map[node2] + ")";
}


std::string VarVarDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + node2->set_name(str_map) + ")";
}


std::string VarParamDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + node2->set_name(str_map) + ")";
}


std::string VarOperatorDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + str_map[node2] + ")";
}


std::string ParamVarDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + node2->set_name(str_map) + ")";
}


std::string ParamParamDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + node2->set_name(str_map) + ")";
}


std::string ParamOperatorDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " / " + str_map[node2] + ")";
}


std::string OperatorVarDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " / " + node2->set_name(str_map) + ")";
}


std::string OperatorParamDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " / " + node2->set_name(str_map) + ")";
}


std::string OperatorOperatorDivideOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " / " + str_map[node2] + ")";
}


std::string VarVarPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + node2->set_name(str_map) + ")";
}


std::string VarParamPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + node2->set_name(str_map) + ")";
}


std::string VarOperatorPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + str_map[node2] + ")";
}


std::string ParamVarPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + node2->set_name(str_map) + ")";
}


std::string ParamParamPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + node2->set_name(str_map) + ")";
}


std::string ParamOperatorPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + node1->set_name(str_map) + " ** " + str_map[node2] + ")";
}


std::string OperatorVarPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " ** " + node2->set_name(str_map) + ")";
}


std::string OperatorParamPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " ** " + node2->set_name(str_map) + ")";
}


std::string OperatorOperatorPowerOperator::set_name(std::unordered_map<std::shared_ptr<Node>, std::string> &str_map)
{
  return "(" + str_map[node1] + " ** " + str_map[node2] + ")";
}


double Expression::evaluate()
{
  for (auto &n : (*nodes))
  {
      n->evaluate();
  }
  value = nodes->back()->value; 
  return value;
}


double Expression::ad(Var &n, bool new_eval)
{
  if (new_eval)
    {
      evaluate();
    }
  for (auto &_n : (*nodes))
  {
      _n->ad(n, new_eval);
  }
  der_n1 = nodes->back()->der_n1;
  return der_n1;
}


double Expression::ad2(Var &n1, Var &n2, bool new_eval)
{
  if (new_eval)
    {
      evaluate();
    }
  for (auto &_n : (*nodes))
  {
      _n->ad2(n1, n2, new_eval);
  }
  der_n1 = nodes->back()->der_n1;
  der_n2 = nodes->back()->der_n2;
  der2 = nodes->back()->der2;
  return der2;
}


bool Expression::has_ad2(Var &n1, Var &n2)
{
  for (auto &_n : (*nodes))
  {
      _n->has_ad2(n1, n2);
  }
  has_der_n1 = nodes->back()->has_der_n1;
  has_der_n2 = nodes->back()->has_der_n2;
  has_der2 = nodes->back()->has_der2;
  return has_der2;
}


std::string Node::_print()
{
  std::unordered_map<std::shared_ptr<Node>, std::string> str_map;
  return set_name(str_map);
}


//int main ()
//{
  //int N = 100000;
  //std::map<int, std::shared_ptr<Var> > x;
  //for (int i = 0; i < N; ++i)
  //  {
  //    x[i] = create_var();
  //  }
  //std::shared_ptr<Node> e = ((*(x[0])) - 1.0)->__pow__(2.0);
  //for (int i = 1; i < N; ++i)
  //  {
  //    e = (*e) + (*(((*(x[i])) - 1.0)->__pow__(2.0)));
  //  }
  //e->evaluate();
  //for (int i = 0; i < N; ++i)
  //  {
  //    e->ad2(*(x[i]), *(x[i]), false, true);
  //  }
//  return 0;
//}
