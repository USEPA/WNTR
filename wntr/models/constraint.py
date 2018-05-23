import logging
from wntr.aml.aml import aml
import wntr.network

logger = logging.getLogger(__name__)


def mass_balance_constraint(m, wn, index_over=None):
    """
    Adds a mass balance to the model for the specified junctions.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names; default is all junctions in wn
    """
    if not hasattr(m, 'mass_balance'):
        m.mass_balance = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        expr = m.expected_demand[node_name]
        for link_name in wn.get_links_for_node(node_name, flag='INLET'):
            expr -= m.flow[link_name]
        for link_name in wn.get_links_for_node(node_name, flag='OUTLET'):
            expr += m.flow[link_name]
        node = wn.get_node(node_name)
        if node.leak_status:
            expr += m.leak_rate[node_name]
        m.mass_balance[node_name] = aml.create_constraint(expr=expr, lb=0, ub=0)


def pdd_mass_balance_constraint(m, wn, index_over=None):
    """
    Adds a mass balance to the model for the specified junctions.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names; default is all junctions in wn
    """
    if not hasattr(m, 'pdd_mass_balance'):
        m.pdd_mass_balance = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        expr = m.demand[node_name]
        for link_name in wn.get_links_for_node(node_name, flag='INLET'):
            expr -= m.flow[link_name]
        for link_name in wn.get_links_for_node(node_name, flag='OUTLET'):
            expr += m.flow[link_name]
        node = wn.get_node(node_name)
        if node.leak_status:
            expr += m.leak_rate[node_name]
        m.pdd_mass_balance[node_name] = aml.create_constraint(expr=expr, lb=0, ub=0)


def hazen_williams_headloss_constraint(m, wn, index_over=None):
    """
    Adds a mass balance to the model for the specified junctions.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of pipe names; default is all pipes in wn
    """
    if not hasattr(m, 'hazen_williams_headloss'):
        m.hazen_williams_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.pipe_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        start_node_name = link.start_node_name
        end_node_name = link.end_node_name
        start_node = wn.get_node(start_node_name)
        end_node = wn.get_node(end_node_name)
        if isinstance(start_node, wntr.network.Junction):
            start_h = m.head[start_node_name]
        else:
            start_h = m.source_head[start_node_name]
        if isinstance(end_node, wntr.network.Junction):
            end_h = m.head[end_node_name]
        else:
            end_h = m.source_head[end_node_name]
        f = m.flow[link_name]
        k = m.hw_resistance[link_name]
        minor_k = m.minor_loss[link_name]
        status = m.status[link_name]

        con = aml.create_conditional_constraint()
        con.lb = 0
        con.ub = 0
        con.add_condition(f + m.hw_q2, status*k*(-f)**m.hw_exp + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f + m.hw_q1, status*k*(-m.hw_a*f**3 + m.hw_b*f**2 - m.hw_c*f + m.hw_d) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f, -(status*k*m.hw_m*f) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q1, status*k*m.hw_m*f + status*minor_k*f**m.hw_minor_exp - status*start_h + status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q2, status*k*(m.hw_a*f**3 + m.hw_b*f**2 + m.hw_c*f + m.hw_d) + status*minor_k*f**m.hw_minor_exp - status*start_h + status*end_h + (1-status)*f)
        con.add_final_expr(status*k*f**m.hw_exp + status*minor_k*f**m.hw_minor_exp - status*start_h + status*end_h + (1-status)*f)
        m.hazen_williams_headloss[link_name] = con


