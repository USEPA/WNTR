import logging
from wntr.aml.aml import aml
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
