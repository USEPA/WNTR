import logging
from wntr.aml.aml import aml
import wntr.network
from wntr.network.base import _DemandStatus

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
        a = m.hw_a
        b = m.hw_b
        c = m.hw_c
        d = m.hw_d

        con = aml.create_conditional_constraint(lb=0, ub=0)
        con.add_condition(f + m.hw_q2, status*k*(-f)**m.hw_exp + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f + m.hw_q1, status*k*(-a*f**3 + b*f**2 - c*f + d) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f, -(status*k*m.hw_m*f) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q1, -status*k*m.hw_m*f - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q2, -status*k*(a*f**3 + b*f**2 + c*f + d) - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_final_expr(-status*k*f**m.hw_exp - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        m.hazen_williams_headloss[link_name] = con


def pdd_constraint(m, wn, index_over=None):
    """
    Adds a pdd constraint to the model for the specified junctions.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names; default is all junctions in wn
    """
    if not hasattr(m, 'pdd'):
        m.pdd = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        h = m.head[node_name]
        d = m.demand[node_name]
        d_expected = m.expected_demand[node_name]
        status = node._demand_status

        if status == _DemandStatus.Partial:
            pmin = m.pmin[node_name]
            pnom = m.pnom[node_name]
            elev = m.elevation[node_name]
            delta = m.pdd_smoothing_delta
            slope = m.pdd_slope
            a1 = m.pdd_poly1_coeffs_a[node_name]
            b1 = m.pdd_poly1_coeffs_b[node_name]
            c1 = m.pdd_poly1_coeffs_c[node_name]
            d1 = m.pdd_poly1_coeffs_d[node_name]
            a2 = m.pdd_poly2_coeffs_a[node_name]
            b2 = m.pdd_poly2_coeffs_b[node_name]
            c2 = m.pdd_poly2_coeffs_c[node_name]
            d2 = m.pdd_poly2_coeffs_d[node_name]
            con = aml.create_conditional_constraint(lb=0, ub=0)
            con.add_condition(h - elev - pmin, d - d_expected*slope*(h-elev-pmin))
            con.add_condition(h - elev - pmin - delta, d - d_expected*(a1*(h-elev)**3 + b1*(h-elev)**2 + c1*(h-elev) + d1))
            con.add_condition(h - elev - pnom + delta, d - d_expected*((h-elev-pmin)/(pnom-pmin))**0.5)
            con.add_condition(h - elev - pnom, d - d_expected*(a2*(h-elev)**3 + b2*(h-elev)**2 + c2*(h-elev) + d2))
            con.add_final_expr(d - d_expected*(slope*(h - elev - pnom) + 1.0))
        elif status == _DemandStatus.Full:
            con = aml.create_constraint(d - d_expected, 0, 0)
        else:
            con = aml.create_constraint(d, 0, 0)

        m.pdd[node_name] = con


def head_pump_headloss_constraint(m, wn, index_over=None):
    """
    Adds a headloss constraint to the model for the head curve pumps.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of HeadPump names; default is all HeadPumps in wn
    """
    if not hasattr(m, 'head_pump_headloss'):
        m.head_pump_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.head_pump_name_list

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
        a = m.hw_a
        b = m.hw_b
        c = m.hw_c
        d = m.hw_d

        con = aml.create_conditional_constraint(lb=0, ub=0)
        con.add_condition(f + m.hw_q2, status*k*(-f)**m.hw_exp + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f + m.hw_q1, status*k*(-a*f**3 + b*f**2 - c*f + d) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f, -(status*k*m.hw_m*f) + status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q1, -status*k*m.hw_m*f - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_condition(f - m.hw_q2, -status*k*(a*f**3 + b*f**2 + c*f + d) - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        con.add_final_expr(-status*k*f**m.hw_exp - status*minor_k*f**m.hw_minor_exp + status*start_h - status*end_h + (1-status)*f)
        m.hazen_williams_headloss[link_name] = con


def plot_constraint(con, var_to_vary, lb, ub):
    import numpy as np
    import matplotlib.pyplot as plt

    x = np.linspace(lb, ub, 10000, True)
    y = []
    for _x in x:
        var_to_vary.value = _x
        y.append(con.evaluate())
    plt.plot(x, y)
    plt.show()
