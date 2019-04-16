import logging
from wntr.sim import aml

logger = logging.getLogger(__name__)


def demand_var(m, wn, index_over=None):
    """
    Add a demand variable to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'demand'):
        m.demand = aml.VarDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        m.demand[node_name] = aml.Var(node.demand_timeseries_list(wn.sim_time))


def flow_var(m, wn, index_over=None):
    """
    Add a flow variable to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of link names
    """
    if not hasattr(m, 'flow'):
        m.flow = aml.VarDict()

    if index_over is None:
        index_over = wn.link_name_list

    for link_name in index_over:
        link = wn.get_link(link_name)
        m.flow[link_name] = aml.Var(0.001)


def head_var(m, wn, index_over=None):
    """
    Add a head variable to the model

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction names
    """
    if not hasattr(m, 'head'):
        m.head = aml.VarDict()

    if index_over is None:
        index_over = wn.junction_name_list

    for node_name in index_over:
        node = wn.get_node(node_name)
        m.head[node_name] = aml.Var(node.elevation)


def leak_rate_var(m, wn, index_over=None):
    """
    Add a variable to the model for leak flow rate

    Parameters
    ----------
    m: wntr.aml.aml.aml.Model
    wn: wntr.network.model.WaterNetworkModel
    index_over: list of str
        list of junction/tank names
    """
    if not hasattr(m, 'leak_rate'):
        m.leak_rate = aml.VarDict()

    if index_over is None:
        index_over = wn.junction_name_list + wn.tank_name_list

    for node_name in index_over:
        m.leak_rate[node_name] = aml.Var(0)

