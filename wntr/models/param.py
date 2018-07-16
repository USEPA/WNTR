import logging
from wntr import aml
from wntr.utils.polynomial_interpolation import cubic_spline
import math
from wntr.network import LinkStatus

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


def leak_coeff_param(m, wn, index_over=None):
    """
    Add a leak discharge coefficient parameter to the model

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction/tank names
    """
    if not hasattr(m, 'leak_coeff'):
        m.leak_coeff = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list + wn.tank_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.leak_coeff:
            m.leak_coeff[node_name].value = node.leak_discharge_coeff
        else:
            m.leak_coeff[node_name] = aml.create_param(value=node.leak_discharge_coeff)


def leak_area_param(m, wn, index_over=None):
    """
    Add a leak discharge coefficient parameter to the model

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction/tank names
    """
    if not hasattr(m, 'leak_area'):
        m.leak_area = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list + wn.tank_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        if node_name in m.leak_area:
            m.leak_area[node_name].value = node.leak_area
        else:
            m.leak_area[node_name] = aml.create_param(value=node.leak_area)


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


def leak_poly_coeffs_param(m, wn, index_over=None):
    """
    Add parameters to the model for leak smoothing polynomial coefficients

    Parameters
    ----------
    m: wntr.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'leak_poly_coeffs_a'):
        m.leak_poly_coeffs_a = aml.ParamDict()
        m.leak_poly_coeffs_b = aml.ParamDict()
        m.leak_poly_coeffs_c = aml.ParamDict()
        m.leak_poly_coeffs_d = aml.ParamDict()

    if index_over is None:
        index_over = wn.junction_name_list + wn.tank_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        x1 = 0.0
        f1 = 0.0
        x2 = x1 + m.leak_delta
        f2 = node.leak_discharge_coeff*node.leak_area*(2.0*9.81*x2)**0.5
        df1 = m.leak_slope
        df2 = 0.5*node.leak_discharge_coeff*node.leak_area*(2.0*9.81)**0.5*x2**(-0.5)
        a, b, c, d = cubic_spline(x1, x2, f1, f2, df1, df2)
        if node_name in m.leak_poly_coeffs_a:
            m.leak_poly_coeffs_a[node_name].value = a
            m.leak_poly_coeffs_b[node_name].value = b
            m.leak_poly_coeffs_c[node_name].value = c
            m.leak_poly_coeffs_d[node_name].value = d
        else:
            m.leak_poly_coeffs_a[node_name] = aml.create_param(value=a)
            m.leak_poly_coeffs_b[node_name] = aml.create_param(value=b)
            m.leak_poly_coeffs_c[node_name] = aml.create_param(value=c)
            m.leak_poly_coeffs_d[node_name] = aml.create_param(value=d)


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
        index_over = wn.pipe_name_list + wn.valve_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = 8.0 * link.minor_loss / (9.81 * math.pi**2 * link.diameter**4)
        if link_name in m.minor_loss:
            m.minor_loss[link_name].value = value
        else:
            m.minor_loss[link_name] = aml.create_param(value=value)


def tcv_resistance_param(m, wn, index_over=None):
    """
    Add a tcv resistance parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of tcv names
    """
    if not hasattr(m, 'tcv_resistance'):
        m.tcv_resistance = aml.ParamDict()

    if index_over is None:
        index_over = wn.tcv_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = 8.0 * link.setting / (9.81 * math.pi**2 * link.diameter**4)
        if link_name in m.tcv_resistance:
            m.tcv_resistance[link_name].value = value
        else:
            m.tcv_resistance[link_name] = aml.create_param(value=value)


def pump_power_param(m, wn, index_over=None):
    """
    Add a power parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of pump names
    """
    if not hasattr(m, 'pump_power'):
        m.pump_power = aml.ParamDict()

    if index_over is None:
        index_over = wn.power_pump_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = link.power
        if link_name in m.pump_power:
            m.pump_power[link_name].value = value
        else:
            m.pump_power[link_name] = aml.create_param(value=value)


def valve_setting_param(m, wn, index_over=None):
    """
    Add a valve setting parameter to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of valve names
    """
    if not hasattr(m, 'valve_setting'):
        m.valve_setting = aml.ParamDict()

    if index_over is None:
        index_over = wn.valve_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        value = link.setting
        if link_name in m.valve_setting:
            m.valve_setting[link_name].value = value
        else:
            m.valve_setting[link_name] = aml.create_param(value=value)
