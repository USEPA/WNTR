"""Model parameters for the WNTRSimulator."""

import logging
from wntr.sim import aml
from wntr.utils.polynomial_interpolation import cubic_spline
import math
from wntr.network import LinkStatus
from wntr.sim.models.utils import ModelUpdater, Definition


logger = logging.getLogger(__name__)


def source_head_param(m, wn):
    """
    Add a head param to the model

    Parameters
    ----------
    m: wntr.sim.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    """
    if not hasattr(m, 'source_head'):
        m.source_head = aml.ParamDict()

        for node_name, node in wn.tanks():
            m.source_head[node_name] = aml.Param(node.head)
        for node_name, node in wn.reservoirs():
            m.source_head[node_name] = aml.Param(node.head_timeseries.at(wn.sim_time))
    else:
        for node_name, node in wn.tanks():
            m.source_head[node_name].value = node.head
        for node_name, node in wn.reservoirs():
            m.source_head[node_name].value = node.head_timeseries.at(wn.sim_time)


def expected_demand_param(m, wn):
    """
    Add a demand parameter to the model

    Parameters
    ----------
    m: wntr.sim.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    """
    demand_multiplier = wn.options.hydraulic.demand_multiplier
    pattern_start = wn.options.time.pattern_start
    
    if not hasattr(m, 'expected_demand'):
        m.expected_demand = aml.ParamDict()

        for node_name, node in wn.junctions():
            m.expected_demand[node_name] = aml.Param(node.demand_timeseries_list.at(wn.sim_time+pattern_start, multiplier=demand_multiplier))
    else:
        for node_name, node in wn.junctions():
            m.expected_demand[node_name].value = node.demand_timeseries_list.at(wn.sim_time+pattern_start, multiplier=demand_multiplier)


class pmin_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a minimum pressure parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
        index_over: list of str
            list of junction names
        """
        if not hasattr(m, 'pmin'):
            m.pmin = aml.ParamDict()

        if index_over is None:
            index_over = wn.junction_name_list

        for node_name in index_over:
            node = wn.get_node(node_name)
            if node.minimum_pressure is None:
                minimum_pressure = wn.options.hydraulic.minimum_pressure
            else:
                minimum_pressure = node.minimum_pressure
                
            if node_name in m.pmin:
                m.pmin[node_name].value = minimum_pressure
            else:
                m.pmin[node_name] = aml.Param(minimum_pressure)

            updater.add(node, 'minimum_pressure', pmin_param.update)


class pnom_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a required pressure parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
        index_over: list of str
            list of junction names
        """
        if not hasattr(m, 'pnom'):
            m.pnom = aml.ParamDict()

        if index_over is None:
            index_over = wn.junction_name_list

        for node_name in index_over:
            node = wn.get_node(node_name)
            if node.required_pressure is None:
                required_pressure = wn.options.hydraulic.required_pressure
            else:
                required_pressure = node.required_pressure
                
            if required_pressure <= m.pdd_smoothing_delta:
                raise ValueError('Required pressure for node %s must be greater than %s, the smoothing delta', node_name, m.pdd_smoothing_delta)
            if node_name in m.pnom:
                m.pnom[node_name].value = required_pressure
            else:
                m.pnom[node_name] = aml.Param(required_pressure)

            updater.add(node, 'required_pressure', pnom_param.update)


class leak_coeff_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a leak discharge coefficient parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.leak_coeff[node_name] = aml.Param(node.leak_discharge_coeff)

            updater.add(node, 'leak_discharge_coeff', leak_coeff_param.update)


class leak_area_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a leak discharge coefficient parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.leak_area[node_name] = aml.Param(node.leak_area)

            updater.add(node, 'leak_area', leak_area_param.update)


class pdd_poly_coeffs_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add parameters to the model for pdd smoothing polynomial coefficients

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
            if node.minimum_pressure is None:
                pmin = wn.options.hydraulic.minimum_pressure
            else:
                pmin = node.minimum_pressure
            if node.required_pressure is None:
                pnom = wn.options.hydraulic.required_pressure
            else:
                pnom = node.required_pressure
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
                m.pdd_poly1_coeffs_a[node_name] = aml.Param(a1)
                m.pdd_poly1_coeffs_b[node_name] = aml.Param(b1)
                m.pdd_poly1_coeffs_c[node_name] = aml.Param(c1)
                m.pdd_poly1_coeffs_d[node_name] = aml.Param(d1)
                m.pdd_poly2_coeffs_a[node_name] = aml.Param(a2)
                m.pdd_poly2_coeffs_b[node_name] = aml.Param(b2)
                m.pdd_poly2_coeffs_c[node_name] = aml.Param(c2)
                m.pdd_poly2_coeffs_d[node_name] = aml.Param(d2)

            updater.add(node, 'minimum_pressure', pdd_poly_coeffs_param.update)
            updater.add(node, 'required_pressure', pdd_poly_coeffs_param.update)


class leak_poly_coeffs_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add parameters to the model for leak smoothing polynomial coefficients

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.leak_poly_coeffs_a[node_name] = aml.Param(a)
                m.leak_poly_coeffs_b[node_name] = aml.Param(b)
                m.leak_poly_coeffs_c[node_name] = aml.Param(c)
                m.leak_poly_coeffs_d[node_name] = aml.Param(d)

            updater.add(node, 'leak_discharge_coeff', leak_poly_coeffs_param.update)
            updater.add(node, 'leak_area', leak_poly_coeffs_param.update)


class elevation_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add an elevation parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.elevation[node_name] = aml.Param(node.elevation)

            updater.add(node, 'elevation', elevation_param.update)


class hw_resistance_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a HW resistance coefficient parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.hw_resistance[link_name] = aml.Param(value)

            updater.add(link, 'roughness', hw_resistance_param.update)
            updater.add(link, 'diameter', hw_resistance_param.update)
            updater.add(link, 'length', hw_resistance_param.update)


class minor_loss_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a minor loss coefficient parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.minor_loss[link_name] = aml.Param(value)

            updater.add(link, 'minor_loss', minor_loss_param.update)
            updater.add(link, 'diameter', minor_loss_param.update)


class tcv_resistance_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a tcv resistance parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.tcv_resistance[link_name] = aml.Param(value)

            updater.add(link, 'setting', tcv_resistance_param.update)
            updater.add(link, 'diameter', tcv_resistance_param.update)


class pump_power_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a power parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.pump_power[link_name] = aml.Param(value)

            updater.add(link, 'power', pump_power_param.update)


class valve_setting_param(Definition):
    @classmethod
    def build(cls, m, wn, updater, index_over=None):
        """
        Add a valve setting parameter to the model

        Parameters
        ----------
        m: wntr.sim.aml.aml.Model
        wn: wntr.network.model.WaterNetworkModel
        updater: ModelUpdater
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
                m.valve_setting[link_name] = aml.Param(value)

            updater.add(link, 'setting', valve_setting_param.update)
