import logging
from wntr import aml
import wntr.network
from wntr.network.base import _DemandStatus
import warnings
from wntr.utils.polynomial_interpolation import cubic_spline
from wntr.network import LinkStatus

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
        if link_name in m.hazen_williams_headloss:
            del m.hazen_williams_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(expr=f, lb=0, ub=0)
        else:
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
            k = m.hw_resistance[link_name]
            minor_k = m.minor_loss[link_name]
            a = m.hw_a
            b = m.hw_b
            c = m.hw_c
            d = m.hw_d

            con = aml.create_conditional_constraint(lb=0, ub=0)
            con.add_condition(f + m.hw_q2, k*(-f)**m.hw_exp + minor_k*f**m.hw_minor_exp + start_h - end_h)
            con.add_condition(f + m.hw_q1, k*(-a*f**3 + b*f**2 - c*f + d) + minor_k*f**m.hw_minor_exp + start_h - end_h)
            con.add_condition(f, -(k*m.hw_m*f) + minor_k*f**m.hw_minor_exp + start_h - end_h)
            con.add_condition(f - m.hw_q1, -k*m.hw_m*f - minor_k*f**m.hw_minor_exp + start_h - end_h)
            con.add_condition(f - m.hw_q2, -k*(a*f**3 + b*f**2 + c*f + d) - minor_k*f**m.hw_minor_exp + start_h - end_h)
            con.add_final_expr(-k*f**m.hw_exp - minor_k*f**m.hw_minor_exp + start_h - end_h)

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
        if node_name in m.pdd:
            del m.pdd[node_name]

        node = wn.get_node(node_name)
        h = m.head[node_name]
        d = m.demand[node_name]
        d_expected = m.expected_demand[node_name]
        status = node._demand_status

        if node._is_isolated:
            con = aml.create_constraint(expr=h, lb=0, ub=0)
        elif status == _DemandStatus.Partial:
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
        if link_name in m.head_pump_headloss:
            del m.head_pump_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(expr=f, lb=0, ub=0)
        else:
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
            A, B, C = link.get_head_curve_coefficients()

            if C <= 1:
                a, b, c, d = get_pump_poly_coefficients(A, B, C, m)
                con = aml.create_conditional_constraint(lb=0, ub=0)
                con.add_condition(f - m.pump_q1, m.pump_slope * f + A - end_h + start_h)
                con.add_condition(f - m.pump_q2, a*f**3 + b*f**2 + c*f + d - end_h + start_h)
                con.add_final_expr(A - B*f**C - end_h + start_h)
            else:
                q_bar, h_bar = get_pump_line_params(A, B, C, m)
                con = aml.create_conditional_constraint(lb=0, ub=0)
                con.add_condition(f - q_bar, m.pump_slope*(f - q_bar) + h_bar - end_h + start_h)
                con.add_final_expr(A - B*f**C - end_h + start_h)

        m.head_pump_headloss[link_name] = con


def power_pump_headloss_constraint(m, wn, index_over=None):
    """
    Adds a headloss constraint to the model for the power pumps.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of powerPump names; default is all powerPumps in wn
    """
    if not hasattr(m, 'power_pump_headloss'):
        m.power_pump_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.power_pump_name_list

    for link_name in index_over:
        if link_name in m.power_pump_headloss:
            del m.power_pump_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(expr=f, lb=0, ub=0)
        else:
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

            con = aml.create_constraint(m.pump_power[link_name] + (start_h - end_h) * f * 9.81 * 1000.0, lb=0, ub=0)
        m.power_pump_headloss[link_name] = con


def prv_headloss_constraint(m, wn, index_over=None):
    """
    Adds a headloss constraint to the model for the power pumps.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of powerPump names; default is all powerPumps in wn
    """
    if not hasattr(m, 'prv_headloss'):
        m.prv_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.prv_name_list

    for link_name in index_over:
        if link_name in m.prv_headloss:
            del m.prv_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(f, lb=0, ub=0)
        else:
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

            if status is wntr.network.LinkStatus.Active:
                con = aml.create_constraint(end_h - m.valve_setting[link_name] - m.elevation[end_node_name], lb=0, ub=0)
            else:
                assert status is LinkStatus.Open
                con = aml.create_constraint(m.minor_loss[link_name]*f**2 - start_h + end_h, lb=0, ub=0)
        m.prv_headloss[link_name] = con


def fcv_headloss_constraint(m, wn, index_over=None):
    """
    Adds a headloss constraint to the model for the power pumps.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of powerPump names; default is all powerPumps in wn
    """
    if not hasattr(m, 'fcv_headloss'):
        m.fcv_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.fcv_name_list

    for link_name in index_over:
        if link_name in m.fcv_headloss:
            del m.fcv_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(f, lb=0, ub=0)
        else:
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

            if status is LinkStatus.Active:
                con = aml.create_constraint(f - m.valve_setting[link_name], lb=0, ub=0)
            else:
                assert status is LinkStatus.Open
                con = aml.create_conditional_constraint(lb=0, ub=0)
                con.add_condition(f, -m.minor_loss[link_name] * f ** 2 - start_h + end_h)
                con.add_final_expr(m.minor_loss[link_name] * f ** 2 - start_h + end_h)
        m.fcv_headloss[link_name] = con


def tcv_headloss_constraint(m, wn, index_over=None):
    """
    Adds a headloss constraint to the model for the power pumps.

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of powerPump names; default is all powerPumps in wn
    """
    if not hasattr(m, 'tcv_headloss'):
        m.tcv_headloss = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.tcv_name_list

    for link_name in index_over:
        if link_name in m.tcv_headloss:
            del m.tcv_headloss[link_name]

        link = wn.get_link(link_name)
        f = m.flow[link_name]
        status = link.status

        if status is LinkStatus.Closed or link._is_isolated:
            con = aml.create_constraint(f, lb=0, ub=0)
        else:
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

            if status is LinkStatus.Active:
                con = aml.create_conditional_constraint(lb=0, ub=0)
                con.add_condition(f, -m.tcv_resistance[link_name] * f ** 2 - start_h + end_h)
                con.add_final_expr(m.tcv_resistance[link_name] * f ** 2 - start_h + end_h)
            else:
                assert status is LinkStatus.Open
                con = aml.create_conditional_constraint(lb=0, ub=0)
                con.add_condition(f, -m.minor_loss[link_name] * f ** 2 - start_h + end_h)
                con.add_final_expr(m.minor_loss[link_name] * f ** 2 - start_h + end_h)
        m.tcv_headloss[link_name] = con


def leak_constraint(m, wn, index_over=None):
    """
    Adds a leak constraint to the model for the specified junctions.

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction/tank names
    """
    if not hasattr(m, 'leak'):
        m.leak_con = aml.ConstraintDict()

    if index_over is None:
        index_over = wn.junction_name_list + wn.tank_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        h = m.head[node_name]
        leak_rate = m.leak_rate[node_name]
        status = node._leak_model_status

        if status == _DemandStatus.Partial:
            elev = m.elevation[node_name]
            delta = m.leak_delta
            slope = m.leak_slope
            a = m.leak_poly_coeffs_a[node_name]
            b = m.leak_poly_coeffs_b[node_name]
            c = m.leak_poly_coeffs_c[node_name]
            d = m.leak_poly_coeffs_d[node_name]
            area = m.leak_area[node_name]
            Cd = m.leak_coeff[node_name]
            con = aml.create_conditional_constraint(lb=0, ub=0)
            con.add_condition(h - elev, leak_rate - slope*(h-elev))
            con.add_condition(h - elev - delta, leak_rate - (a*(h-elev)**3 + b*(h-elev)**2 + c*(h-elev) + d))
            con.add_final_expr(leak_rate - Cd*area*(2.0*9.81*(h-elev))**0.5)
        elif status == _DemandStatus.Zero:
            con = aml.create_constraint(leak_rate, 0, 0)
        else:
            raise ValueError('Unrecognized _DemandStatus for node {0}: {1}'.format(node_name, status))

        m.leak_con[node_name] = con


def plot_constraint(con, var_to_vary, lb, ub, with_derivative=True, show_plot=True):
    import numpy as np
    import matplotlib.pyplot as plt

    x = np.linspace(lb, ub, 10000, True)
    y = []
    dy = []
    for _x in x:
        var_to_vary.value = _x
        y.append(con.evaluate())
        dy.append(con.ad(var_to_vary, False))
    plt.subplot(2, 1, 1)
    plt.plot(x, y)
    plt.title(con.name)
    plt.ylabel('residual')
    plt.subplot(2, 1, 2)
    plt.plot(x, dy)
    plt.ylabel('derivative')
    plt.xlabel(var_to_vary.name)
    if show_plot:
        plt.show()


def get_pump_poly_coefficients(A, B, C, m):
    q1 = m.pump_q1
    q2 = m.pump_q2
    m = m.pump_slope

    f1 = m*q1 + A
    f2 = A - B*q2**C
    df1 = m
    df2 = -B*C*q2**(C-1.0)

    a,b,c,d = cubic_spline(q1, q2, f1, f2, df1, df2)

    if a <= 0.0 and b <= 0.0:
        return a, b, c, d
    elif a > 0.0 and b > 0.0:
        if df2 < 0.0:
            return a, b, c, d
        else:
            logger.warning('Pump smoothing polynomial is not monotonically decreasing.')
            warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
            return a, b, c, d
    elif a > 0.0 and b <= 0.0:
        if df2 < 0.0:
            return a, b, c, d
        else:
            logger.warning('Pump smoothing polynomial is not monotonically decreasing.')
            warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
            return a, b, c, d
    elif a <= 0.0 and b > 0.0:
        if q2 <= -2.0*b/(6.0*a) and df2 < 0.0:
            return a, b, c, d
        else:
            logger.warning('Pump smoothing polynomial is not monotonically decreasing.')
            warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
            return a, b, c, d
    else:
        logger.warning('Pump smoothing polynomial is not monotonically decreasing.')
        warnings.warn('Pump smoothing polynomial is not monotonically decreasing.')
        return a, b, c, d


def get_pump_line_params(A, B, C, m):
    q_bar = (m.pump_slope/(-B*C))**(1.0/(C-1.0))
    h_bar = A - B*q_bar**C
    return q_bar, h_bar
