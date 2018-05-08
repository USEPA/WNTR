#include "expression.hpp"

class Component
class Constraint
class Objective
class ConditionalConstraint


class Component
{
public:
    Component() = default;
    virtual ~Component() = default;
    virtual double evaluate();
    virtual double ad(Var&, bool);
    virtual double ad2(Var&, Var&, bool);
}


class Objective
{
public:
    Objective() = default;
    explicit Objective(std::shared_ptr<Node> e): expr(e) {}
    std::shared_ptr<Node> expr;
    double evaluate() override;
    double ad(Var&, bool) override;
    double ad2(Var&, Var&, bool) override;
}


class Constraint
{
public:
    Constraint() = default;
    explicit Constraint(std::shared_ptr<Node> e, double lower, double upper): expr(e) {}
    std::shared_ptr<Node> expr;
    double lb = -1.0e20;
    double ub = 1.0e20;
    double dual = 0.0;
    double evaluate() override;
    double ad(Var&, bool) override;
    double ad2(Var&, Var&, bool) override;
}


class