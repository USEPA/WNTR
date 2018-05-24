import logging
from wntr.aml.aml import aml
from wntr.utils.polynomial_interpolation import cubic_spline
import math

print(aml)

logger = logging.getLogger(__name__)


def source_head_param(m, wn, index_over=None):
    """
    Add a head param to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of tank/reservoir names
    """
    if not hasattr(m, 'source_head'):
        m.source_head = aml.ParamDict()

    if index_over is None:
        index_over = wn.tank_name_list + wn.reservoir_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        m.source_head[node_name] = aml.create_param(value=node.head)


def expected_demand_param(m, wn, index_over=None):
    """
    Add a demand parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'expected_demand'):
        m.expected_demand = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.expected_demand:
            m.expected_demand[node_name].value = node.demand_timeseries_list(wn.sim_time)
        else:
            m.expected_demand[node_name] = aml.create_param(value=node.demand_timeseries_list(wn.sim_time))


def pmin_param(m, wn, index_over=None):
    """
    Add a minimum pressure parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'pmin'):
        m.pmin = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.pmin:
            m.pmin[node_name].value = node.minimum_pressure
        else:
            m.pmin[node_name] = aml.create_param(value=node.minimum_pressure)


def pnom_param(m, wn, index_over=None):
    """
    Add a nominal pressure parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'pnom'):
        m.pnom = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.pnom:
            m.pnom[node_name].value = node.nominal_pressure
        else:
            m.pnom[node_name] = aml.create_param(value=node.nominal_pressure)


def pdd_poly_coeffs_param(m, wn, index_over=None):
    """
    Add parameters to the model for pdd smoothing polynomial coefficients

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'pdd_poly1_coeffs_a'):
        m.pdd_poly1_coeffs_a = aml.ParamDict()
        m.pdd_poly1_coeffs_b = aml.ParamDict()
        m.pdd_poly1_coeffs_c = aml.ParamDict()
        m.pdd_poly1_coeffs_d = aml.ParamDict()
        m.pdd_poly2_coeffs_a = aml.ParamDict()
        m.pdd_poly2_coeffs_b = aml.ParamDict()
        m.pdd_poly2_coeffs_c = aml.ParamDict()
        m.pdd_poly2_coeffs_d = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        pmin = node.minimum_pressure
        pnom = node.nominal_pressure
        x1 = pmin
        f1 = 0.0
        x2 = pmin + m.pdd_smoothing_delta
        f2 = ((x2 - pmin)/(pnom-pmin))**0.5
        df1 = m.pdd_slope
        df2 = 0.5*((x2-pmin)/(pnom-pmin))**(-0.5)*1.0/(pnom-pmin)
        a1, b1, c1, d1 = cubic_spline(x1, x2, f1, f2, df1, df2)
        x1 = pnom-m.pdd_smoothing_delta
        f1 = ((x1-pmin)/(pnom-pmin))**0.5
        x2 = pnom
        f2 = 1.0
        df1 = 0.5*((x1-pmin)/(pnom-pmin))**(-0.5)*1.0/(pnom-pmin)
        df2 = m.pdd_slope
        a2, b2, c2, d2 = cubic_spline(x1, x2, f1, f2, df1, df2)
        if node_name in m.pdd_poly1_coeffs_a:
            m.pdd_poly1_coeffs_a[node_name].value = a1
            m.pdd_poly1_coeffs_b[node_name].value = b1
            m.pdd_poly1_coeffs_c[node_name].value = c1
            m.pdd_poly1_coeffs_d[node_name].value = d1
            m.pdd_poly2_coeffs_a[node_name].value = a2
            m.pdd_poly2_coeffs_b[node_name].value = b2
            m.pdd_poly2_coeffs_c[node_name].value = c2
            m.pdd_poly2_coeffs_d[node_name].value = d2
        else:
            m.pdd_poly1_coeffs_a[node_name] = aml.create_param(value=a1)
            m.pdd_poly1_coeffs_b[node_name] = aml.create_param(value=b1)
            m.pdd_poly1_coeffs_c[node_name] = aml.create_param(value=c1)
            m.pdd_poly1_coeffs_d[node_name] = aml.create_param(value=d1)
            m.pdd_poly2_coeffs_a[node_name] = aml.create_param(value=a2)
            m.pdd_poly2_coeffs_b[node_name] = aml.create_param(value=b2)
            m.pdd_poly2_coeffs_c[node_name] = aml.create_param(value=c2)
            m.pdd_poly2_coeffs_d[node_name] = aml.create_param(value=d2)


def elevation_param(m, wn, index_over=None):
    """
    Add an elevation parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'elevation'):
        m.elevation = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.elevation:
            m.elevation[node_name].value = node.elevation
        else:
            m.elevation[node_name] = aml.create_param(value=node.elevation)


def hw_resistance_param(m, wn, index_over=None):
    """
    Add a HW resistance coefficient parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of pipe names
    """
    if not hasattr(m, 'hw_resistance'):
        m.hw_resistance = aml.ParamDict()

    if index_over is None:
        index_over = wn.pipe_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = m.hw_k * link.roughness**(-1.852) * link.diameter**(-4.871) * link.length
        if link_name in m.hw_resistance:
            m.hw_resistance[link_name].value = value
        else:
            m.hw_resistance[link_name] = aml.create_param(value=value)


def minor_loss_param(m, wn, index_over=None):
    """
    Add a minor loss coefficient parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of pipe names
    """
    if not hasattr(m, 'minor_loss'):
        m.minor_loss = aml.ParamDict()

    if index_over is None:
        index_over = wn.pipe_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = 8.0 * link.minor_loss / (9.81 * math.pi**2 * link.diameter**4)
        if link_name in m.minor_loss:
            m.minor_loss[link_name].value = value
        else:
            m.minor_loss[link_name] = aml.create_param(value=value)


def status_param(m, wn, index_over=None):
    """
    Add a status parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of pipe names
    """
    if not hasattr(m, 'status'):
        m.status = aml.ParamDict()

    if index_over is None:
        index_over = wn.pipe_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = link.status
        if link_name in m.status:
            m.status[link_name].value = value
        else:
            m.status[link_name] = aml.create_param(value=value)