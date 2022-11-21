import wntr.sim.hydraulics
from wntr.sim.solvers import NewtonSolver, SolverStatus
import wntr.sim.results
import numpy as np
import warnings
import time
import sys
import logging
import scipy.optimize
import scipy.sparse
import scipy.sparse.csr
import itertools
from collections import OrderedDict
from wntr.utils.ordered_set import OrderedSet
from wntr.network import Junction, Pipe, Valve, Pump, Tank, Reservoir, LinkStatus, WaterNetworkModel, Link
from wntr.sim.network_isolation import check_for_isolated_junctions, get_long_size
from wntr.sim.aml.aml import VarDict, ParamDict
from wntr.sim.aml.expr import Var, Param
from wntr.network.controls import (AndCondition, Comparison, Control, ControlAction,
                                   ControlChangeTracker, ControlChecker, ControlPriority, OrCondition,
                                   RelativeCondition, Rule, SimTimeCondition,
                                   TankLevelCondition, TimeOfDayCondition, ValueCondition,
                                   _ActiveFCVCondition, _ActivePRVCondition,
                                   _ActivePSVCondition, _CloseCVCondition,
                                   _CloseHeadPumpCondition, _ClosePowerPumpCondition,
                                   _ClosePRVCondition, _ClosePSVCondition, _ControlType,
                                   _InternalControlAction, _OpenCVCondition,
                                   _OpenFCVCondition, _OpenHeadPumpCondition,
                                   _OpenPowerPumpCondition, _OpenPRVCondition,
                                   _OpenPSVCondition, FunctionCondition, Observer,
                                   ControlBase, BaseControlAction)
from typing import Optional
import networkx as nx
import enum
import pandas as pd
import json
import os
try:
    import plotly
except ImportError:
    pass

logger = logging.getLogger(__name__)


# TODO: allow user to turn of demand status and leak model status controls
# TODO: allow user to switch between wntr and ipopt models


class WaterNetworkSimulator(object):
    """
    Base water network simulator class.

    wn : WaterNetworkModel object
        Water network model

    .. warning::

        The mode parameter has been deprecated. Please set the mode using the network option,
        wn.options.hydraulic.demand_model.

    
    """

    def __init__(self, wn=None):

        self._wn = wn
        # self.mode = mode
        self.mode = self._wn.options.hydraulic.demand_model


    def _get_link_type(self, name):
        if isinstance(self._wn.get_link(name), Pipe):
            return 'pipe'
        elif isinstance(self._wn.get_link(name), Valve):
            return 'valve'
        elif isinstance(self._wn.get_link(name), Pump):
            return 'pump'
        else:
            raise RuntimeError('Link name ' + name + ' was not recognised as a pipe, valve, or pump.')

    def _get_node_type(self, name):
        if isinstance(self._wn.get_node(name), Junction):
            return 'junction'
        elif isinstance(self._wn.get_node(name), Tank):
            return 'tank'
        elif isinstance(self._wn.get_node(name), Reservoir):
            return 'reservoir'
        else:
            raise RuntimeError('Node name ' + name + ' was not recognised as a junction, tank, reservoir, or leak.')


class _DiagnosticsOptions(enum.IntEnum): # pragma: no cover
    plot_network = 1
    disable = 2
    run_until_time = 3
    perform_next_step = 4
    load_solution_from_json = 5
    display_residuals = 6
    compare_link_status_to_solution = 7
    compare_link_sol = 8
    store_var_values_in_network = 9


class _Diagnostics(object): # pragma: no cover
    def __init__(self, wn, model, mode, enable=False):
        self.wn = wn
        self.model = model
        # self.mode = mode
        self.mode = wn.options.hydraulic.demand_model
        self.enabled = enable
        self.time_to_enable = -1

    def get_command(self):
        print('please select what you would like to do:')
        for option in _DiagnosticsOptions:
            print('  {0} - {1}'.format(option.value, option.name))
        selection = int(input())
        return selection

    def run(self, last_step, next_step):
        if self.enabled and self.wn.sim_time >= self.time_to_enable:
            print('last step: ', last_step)
            print('next step: ', next_step)
            selection = self.get_command()
            if selection == _DiagnosticsOptions.plot_network:
                self._plot_interactive_network(self.wn)
                self.run(last_step, next_step)
            elif selection == _DiagnosticsOptions.disable:
                self.enabled = False
            elif selection == _DiagnosticsOptions.run_until_time:
                self.time_to_enable = float(input('What sim time should diagnostics be enabled at? '))
            elif selection == _DiagnosticsOptions.perform_next_step:
                pass
            elif selection == _DiagnosticsOptions.load_solution_from_json:
                self.load_solution_from_json()
                self.run(last_step, next_step)
            elif selection == _DiagnosticsOptions.display_residuals:
                self.display_residuals()
                self.run(last_step, next_step)
            elif selection == _DiagnosticsOptions.compare_link_status_to_solution:
                self.compare_link_status_to_solution()
                self.run(last_step, next_step)
            elif selection == _DiagnosticsOptions.compare_link_sol:
                self.compare_link_sol()
                self.run(last_step, next_step)
            elif selection == _DiagnosticsOptions.store_var_values_in_network:
                self.store_var_values_in_network()
                self.run(last_step, next_step)

    def compare_link_status_to_solution(self):
        if int(self.wn.sim_time) != self.wn.sim_time:
            raise ValueError('wn.sim_time must be an int')
        t = int(self.wn.sim_time)
        json_file = input('path to json file: ')
        f = open(json_file, 'r')
        sol = json.load(f)
        f.close()
        if str(t) not in sol:
            print('no solution found for sim_time {0}'.format(t))
            return
        sol = sol[str(t)]
        index = list()
        wntr_stat = list()
        sol_stat = list()
        stat_diff = list()
        for link_name, stat in sol.items():
            link = self.wn.get_link(link_name)
            index.append(link_name)
            wntr_stat.append(link.status)
            sol_stat.append(stat)
            if link.status == stat:
                stat_diff.append(0)
            else:
                stat_diff.append(1)
        df = pd.DataFrame({'wntr status': wntr_stat, 'sol status': sol_stat, 'diff': stat_diff}, index=index)
        df.sort_values(by=['diff'], axis=0, ascending=False, inplace=True)
        html_str = df.to_html()
        f = open('status_comparison_' + str(int(self.wn.sim_time)) + '.html', 'w')
        f.write(html_str)
        f.close()
        os.system('open status_comparison_' + str(int(self.wn.sim_time)) + '.html')

    def load_solution_from_json(self):
        if int(self.wn.sim_time) != self.wn.sim_time:
            raise ValueError('wn.sim_time must be an int')
        t = int(self.wn.sim_time)
        json_file = input('Path to json file: ')
        f = open(json_file, 'r')
        sol = json.load(f)
        f.close()
        if str(t) not in sol:
            print('no solution found for sim_time {0}'.format(t))
            return
        sol = sol[str(t)]
        for v_name, val in sol.items():
            if not hasattr(self.model, v_name):
                print('could not load {0} into the model because {0} is not an attribute of the model'.format(v_name))
                continue
            v = getattr(self.model, v_name)
            if type(val) == dict:
                for key, _val in val.items():
                    if key not in v:
                        print('could not load {0}[{1}] into the model because {1} is not an element in model.{0}'.format(v_name, key))
                        continue
                    _v = v[key]
                    if type(_v) == Var:
                        _v.value = _val
                    else:
                        if abs(_v.value - _val) > 1e-6:
                            if abs(_val) <= 1e-8 or abs(_v.value - _val)/abs(_val) > 1e-6:
                                print('found difference between {0} values for {1}'.format(type(_v), str(_v)))
                                print('  from solution file: {0}'.format(_val))
                                print('  from model: {0}'.format(_v.value))
            else:
                if type(v) == Var:
                    v.value = val
                else:
                    if abs(v.value - val) > 1e-6:
                        if abs(val) <= 1e-8 or abs(v.value - val)/abs(val) > 1e-6:
                            print('found difference between {0} values for {1}'.format(type(v), str(v)))
                            print('  from solution file: {0}'.format(val))
                            print('  from model: {0}'.format(v.value))

    def display_residuals(self):
        self.model.set_structure()
        r = abs(self.model.evaluate_residuals())

        index = list()
        resids = list()
        for c in self.model.cons():
            index.append(c.name)
            resids.append(r[c.index])
        all_resids = pd.DataFrame({'resids': resids}, index=index)
        all_resids.sort_values(by=['resids'], axis=0, ascending=False, inplace=True)
        html_str = all_resids.to_html()
        f = open('resids_' + str(int(self.wn.sim_time)) + '.html', 'w')
        f.write(html_str)
        f.close()
        os.system('open resids_' + str(int(self.wn.sim_time)) + '.html')

    def compare_link_sol(self):
        link_name = input('link: ')
        if int(self.wn.sim_time) != self.wn.sim_time:
            raise ValueError('wn.sim_time must be an int')
        t = int(self.wn.sim_time)
        json_file = input('Path to json file: ')
        f = open(json_file, 'r')
        sol = json.load(f)
        f.close()
        if str(t) not in sol:
            print('no solution found for sim_time {0}'.format(t))
            return
        sol = sol[str(t)]

        link = self.wn.get_link(link_name)
        start_node = link.start_node
        end_node = link.end_node

        df = pd.DataFrame({'wntr': np.ones(7) * np.nan,
                           'sol': np.ones(7) * np.nan},
                          index=['flow', 'start_head', 'end_head', 'x_coord', 'y_coord', 'start_node', 'end_node'])

        df.at['flow', 'wntr'] = self.model.flow[link_name].value
        df.at['flow', 'sol'] = sol['flow'][link_name]

        if isinstance(start_node, wntr.network.Junction):
            df.at['start_head', 'wntr'] = self.model.head[start_node.name].value
            df.at['start_head', 'sol'] = sol['head'][start_node.name]
        else:
            df.at['start_head', 'wntr'] = self.model.source_head[start_node.name].value
            df.at['start_head', 'sol'] = sol['source_head'][start_node.name]
        if isinstance(end_node, wntr.network.Junction):
            df.at['end_head', 'wntr'] = self.model.head[end_node.name].value
            df.at['end_head', 'sol'] = sol['head'][end_node.name]
        else:
            df.at['end_head', 'wntr'] = self.model.source_head[end_node.name].value
            df.at['end_head', 'sol'] = sol['source_head'][end_node.name]

        df.at['x_coord', 'wntr'] = 0.5 * (start_node.coordinates[0] + end_node.coordinates[0])
        df.at['x_coord', 'sol'] = 0.5 * (start_node.coordinates[0] + end_node.coordinates[0])
        df.at['y_coord', 'wntr'] = 0.5 * (start_node.coordinates[1] + end_node.coordinates[1])
        df.at['y_coord', 'sol'] = 0.5 * (start_node.coordinates[1] + end_node.coordinates[1])
        df.at['start_node', 'wntr'] = start_node.name
        df.at['start_node', 'sol'] = start_node.name
        df.at['end_node', 'wntr'] = end_node.name
        df.at['end_node', 'sol'] = end_node.name

        html_str = df.to_html()
        f = open('link_comparison_' + link_name + '_' + str(t) + '.html', 'w')
        f.write(html_str)
        f.close()
        os.system('open link_comparison_' + link_name + '_' + str(t) + '.html')

    def store_var_values_in_network(self):
        # self.mode = self._wn.options.hydraulic.demand_model
        wntr.sim.hydraulics.store_results_in_network(self.wn, self.model) #, self.mode)

    @classmethod
    def _plot_interactive_network(cls, wn, title=None, node_size=8, link_width=2,
                                  figsize=None, round_ndigits=3, filename=None, auto_open=True):
        """
        Create an interactive scalable network graphic using networkx and plotly.

        Parameters
        ----------
        wn : wntr WaterNetworkModel
            A WaterNetworkModel object

        title : str, optional
            Plot title (default = None)

        node_size : int, optional
            Node size (default = 8)

        link_width : int, optional
            Link width (default = 1)

        figsize: list, optional
            Figure size in pixels, default= [700, 450]

        round_ndigits : int, optional
            Number of digits to round node values used in the label (default = 2)

        filename : string, optional
            HTML file name (default=None, temp-plot.html)
        """
        if figsize is None:
            figsize = [1000, 700]

        node_attributes = ['_is_isolated', 'head', 'demand']
        link_attributes = ['status', '_is_isolated', 'flow']

        # Graph
        G = wn.to_graph()

        open_edges = dict()
        closed_edges = dict()
        isolated_edges = dict()
        for edge_dict in [open_edges, closed_edges, isolated_edges]:
            edge_dict['x'] = list()
            edge_dict['y'] = list()
        for edge in G.edges:
            x0, y0 = G.nodes[edge[0]]['pos']
            x1, y1 = G.nodes[edge[1]]['pos']
            link = wn.get_link(edge[2])
            if link._is_isolated:
                edge_dict = isolated_edges
            elif link.status == LinkStatus.Opened or link.status == LinkStatus.Active:
                edge_dict = open_edges
            elif link.status == LinkStatus.Closed:
                edge_dict = closed_edges
            else:
                raise ValueError('Unexpected link status: {0}'.format(str(link.status)))
            edge_dict['x'] += tuple([x0, x1, None])
            edge_dict['y'] += tuple([y0, y1, None])

        open_edge_trace = plotly.graph_objs.Scatter(x=open_edges['x'], y=open_edges['y'], mode='lines',
                                                    line=dict(color='Blue', width=link_width))
        closed_edge_trace = plotly.graph_objs.Scatter(x=closed_edges['x'], y=closed_edges['y'], mode='lines',
                                                    line=dict(color='Yellow', width=link_width))
        isolated_edge_trace = plotly.graph_objs.Scatter(x=isolated_edges['x'], y=isolated_edges['y'], mode='lines',
                                                        line=dict(color='Red', width=link_width))

        edge_name_trace = plotly.graph_objs.Scatter(x=[], y=[], text=[], hoverinfo='text', mode='markers',
                                                    marker=dict(size=1))
        for edge in G.edges:
            x0, y0 = G.nodes[edge[0]]['pos']
            x1, y1 = G.nodes[edge[1]]['pos']
            link = wn.get_link(edge[2])
            edge_name_trace['x'] += tuple([0.5 * (x0 + x1)])
            edge_name_trace['y'] += tuple([0.5 * (y0 + y1)])
            link_text = str(link.link_type) + ' ' + str(link)
            for _attr in link_attributes:
                val = getattr(link, _attr)
                if type(val) == float:
                    val = round(val, round_ndigits)
                link_text += '<br />{0}: {1}'.format(_attr, str(val))
            link_text += '<br />{0}: {1}'.format('x_coord', 0.5 * (x0 + x1))
            link_text += '<br />{0}: {1}'.format('y_coord', 0.5 * (y0 + y1))
            edge_name_trace['text'] += tuple([link_text])

        # Create node trace
        node_trace = plotly.graph_objs.Scatter(x=[], y=[], text=[], hoverinfo='text', mode='markers',
                                            marker=dict(size=node_size, color='Black', line=dict(width=1)))
        for node in G.nodes():
            x, y = G.nodes[node]['pos']
            node_trace['x'] += tuple([x])
            node_trace['y'] += tuple([y])
            _node = wn.get_node(node)
            node_text = str(_node.node_type) + ' ' + str(_node)
            for _attr in node_attributes:
                val = getattr(_node, _attr)
                if type(val) == float:
                    val = round(val, round_ndigits)
                node_text += '<br />{0}: {1}'.format(_attr, str(val))
            try:
                if hasattr(_node, 'elevation'):
                    node_text += '<br />{0}: {1}'.format('pressure', round(_node.head-_node.elevation, round_ndigits))
            except:
                pass
            node_text += '<br />{0}: {1}'.format('x_coord', x)
            node_text += '<br />{0}: {1}'.format('y_coord', y)
            node_trace['text'] += tuple([node_text])

        # Create figure
        data = [open_edge_trace, closed_edge_trace, isolated_edge_trace, edge_name_trace, node_trace]
        layout = plotly.graph_objs.Layout(title=title,
                                        titlefont=dict(size=16),
                                        showlegend=False,
                                        width=figsize[0],
                                        height=figsize[1],
                                        hovermode='closest',
                                        margin=dict(b=20, l=5, r=5, t=40),
                                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))

        fig = plotly.graph_objs.Figure(data=data, layout=layout)
        if filename:
            plotly.offline.plot(fig, filename=filename, auto_open=auto_open)
        else:
            plotly.offline.plot(fig, filename='network_state_at_' + str(int(wn.sim_time)) + '.html', auto_open=auto_open)

    @classmethod
    def _write_DD_results_to_json_for_diagnostics(cls, wn, res, filename):
        d = dict()
        mode = wn.options.hydraulic.demand_model
        if mode in ['DD','DDA']:
            demand_key = 'expected_demand'
        elif mode in ['PDD','PDA']:
            demand_key = 'demand'
        else:
            raise ValueError('Unexpected mode: {0}'.format(mode))

        for t in res.node['head'].index:
            d[t] = dict()
            d[t]['head'] = dict()
            d[t]['source_head'] = dict()
            d[t][demand_key] = dict()
            d[t]['flow'] = dict()
            for col in res.node['head'].columns:
                node = wn.get_node(col)
                if node.node_type in {'Tank', 'Reservoir'}:
                    d[t]['source_head'][col] = float(res.node['head'].at[t, col])
                else:
                    d[t]['head'][col] = float(res.node['head'].at[t, col])
            for col in res.node['demand'].columns:
                node = wn.get_node(col)
                if node.node_type in {'Tank', 'Reservoir'}:
                    pass
                else:
                    d[t][demand_key][col] = float(res.node['demand'].at[t, col])
            for col in res.link['flowrate'].columns:
                d[t]['flow'][col] = float(res.link['flowrate'].at[t, col])

        f = open(filename, 'w')
        json.dump(d, f)
        f.close()

    @classmethod
    def _write_status_to_json(cls, wn, res, filename):
        d = dict()

        for t in res.link['status'].index:
            d[t] = dict()
            for col in res.link['status'].columns:
                d[t][col] = int(res.link['status'].at[t, col])

        f = open(filename, 'w')
        json.dump(d, f)
        f.close()


def _check_upstream_sources(graph, wn, valve):
    if valve.status != LinkStatus.Active:
        return False

    graph.remove_edge(valve.start_node, valve.end_node, valve)
    res = False

    upstream_nodes = nx.algorithms.descendants(graph, valve.start_node)
    has_upstream_source = False
    for tank_name, tank in wn.tanks():
        if tank in upstream_nodes:
            has_upstream_source = True
            break
    for r_name, reservoir in wn.reservoirs():
        if reservoir in upstream_nodes:
            has_upstream_source = True
            break
    if not has_upstream_source:
        res = True

    graph.add_edge(valve.start_node, valve.end_node, valve)
    return res


def _check_downstream_sources(graph, wn, valve):
    if valve.status != LinkStatus.Active:
        return False

    graph.remove_edge(valve.start_node, valve.end_node, valve)
    res = False

    downstream_nodes = nx.algorithms.descendants(graph, valve.end_node)
    has_downstream_source = False
    for tank_name, tank in wn.tanks():
        if tank in downstream_nodes:
            has_downstream_source = True
            break
    for r_name, reservoir in wn.reservoirs():
        if reservoir in downstream_nodes:
            has_downstream_source = True
            break
    if not has_downstream_source:
        res = True

    graph.add_edge(valve.start_node, valve.end_node, valve)
    return res


class _ValveSourceChecker(Observer):
    def __init__(self, wn):
        self.wn = wn
        self.graph = nx.MultiGraph()
        self.graph.add_nodes_from([n for n_name, n in wn.nodes()])
        self.graph.add_edges_from([(l.start_node, l.end_node, l) for l_name, l in wn.links() if l.status != LinkStatus.Closed])
        self._previous_values = dict()
        self._values_at_last_compute = dict()
        self._needs_compute = True
        self._cached_results = dict()
        self._first_compute = True

    def update(self, action: BaseControlAction):
        obj, attr = action.target()
        val = getattr(obj, attr)
        if val != self._previous_values[(obj, attr)]:
            self._needs_compute = True
            if val == wntr.network.LinkStatus.Closed:
                self.graph.remove_edge(obj.start_node, obj.end_node, obj)
            else:
                self.graph.add_edge(obj.start_node, obj.end_node, obj)

        self._previous_values[(obj, attr)] = val

    def register_control(self, control: ControlBase):
        for action in control.actions():
            obj, attr = action.target()
            if isinstance(obj, Link) and attr == 'status':
                action.subscribe(self)
                self._previous_values[(obj, attr)] = getattr(obj, attr)

    def _cache_values_at_compute(self):
        for key, val in self._previous_values.items():
            self._values_at_last_compute[key] = val

    def _changes_since_compute(self):
        for k, v in self._values_at_last_compute.items():
            if v != self._previous_values[k]:
                return True
        return False

    def _compute(self):
        if self._first_compute or (self._needs_compute and self._changes_since_compute()):
            self._first_compute = False
            self._cache_values_at_compute()
            for valve_name, valve in self.wn.prvs():
                self._cached_results[valve] = _check_upstream_sources(self.graph, self.wn, valve)

            for valve_name, valve in self.wn.psvs():
                self._cached_results[valve] = _check_downstream_sources(self.graph, self.wn, valve)

            for valve_name, valve in self.wn.fcvs():
                upstream_res = _check_upstream_sources(self.graph, self.wn, valve)
                downstream_res = _check_downstream_sources(self.graph, self.wn, valve)
                self._cached_results[valve] = upstream_res or downstream_res
        self._needs_compute = False

    def should_valve_be_opened(self, valve: Valve):
        """
        This is a function to be used with a FunctionCondition to ensure PRVs are connected to at least one upstream
        source, PSVs are connected to at least one downstream source, and FCVs are connected to at least one
        upstream source and at least one downstream source. If these conditions are not satisifed, the valve
        should be opened (the internal status).
        """
        self._compute()
        return self._cached_results[valve]


class WNTRSimulator(WaterNetworkSimulator):
    """
    WNTR simulator class.
    The WNTR simulator uses a custom newton solver and linear solvers from scipy.sparse.

    Parameters
    ----------
    wn : WaterNetworkModel object
        Water network model


    .. note::
    
        The mode parameter has been deprecated. Please set the mode using Options.hydraulic.demand_model

    """

    def __init__(self, wn):

        super(WNTRSimulator, self).__init__(wn)

        # attributes needed isolated junctions/links
        self._prev_isolated_junctions = OrderedSet()
        self._prev_isolated_links = OrderedSet()
        self._internal_graph = None
        self._node_pairs_with_multiple_links = None
        self._link_name_to_id = OrderedDict()
        self._link_id_to_name = OrderedDict()
        self._node_name_to_id = OrderedDict()
        self._node_id_to_name = OrderedDict()
        self._source_ids = None

        # attributes needed for controls
        self._presolve_controls = ControlChecker()
        self._rules = ControlChecker()
        self._postsolve_controls = ControlChecker()
        self._feasibility_controls = ControlChecker()
        self._change_tracker = ControlChangeTracker()
        self._model_updater = None
        self._rule_iter = 0

        # attributes needed for solver
        self._model = None
        self._solver = NewtonSolver()
        self._backup_solver = None
        self._solver_options = dict()
        self._backup_solver_options = dict()
        self._convergence_error = False

        # other attributes
        self._hydraulic_timestep = None
        self._report_timestep = None

        self._Htol = 0.0001524  # Head tolerance in meters.
        self._Qtol = 2.83168e-6  # Flow tolerance in m^3/s.

        self._valve_source_checker: Optional[_ValveSourceChecker] = None

        long_size = get_long_size()
        if long_size == 4:
            self._int_dtype = np.int32
        else:
            assert long_size == 8
            self._int_dtype = np.int64

        self._initialize_name_id_maps()

    def _get_time(self):
        s = int(self._wn.sim_time)
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        s = int(s)
        return '{:02}:{:02}:{:02}'.format(h, m, s)

    def _setup_sim_options(self, solver, backup_solver, solver_options, backup_solver_options, convergence_error):
        self._report_timestep = self._wn.options.time.report_timestep
        self._hydraulic_timestep = self._wn.options.time.hydraulic_timestep
        if type(self._report_timestep) is str:
            if self._report_timestep.upper() != 'ALL':
                raise ValueError('report timestep must be either an integer number of seconds or "ALL".')
        else:
            if self._report_timestep < self._hydraulic_timestep:
                msg = 'The report timestep must be an integer multiple of the hydraulic timestep. Reducing the hydraulic timestep from {0} seconds to {1} seconds for this simulation.'.format(self._hydraulic_timestep, self._report_timestep)
                logger.warning(msg)
                warnings.warn(msg)
                self._hydraulic_timestep = self._report_timestep
            elif self._report_timestep%self._hydraulic_timestep != 0:
                new_report = self._report_timestep - (self._report_timestep%self._hydraulic_timestep)
                msg = 'The report timestep must be an integer multiple of the hydraulic timestep. Reducing the report timestep from {0} seconds to {1} seconds for this simulation.'.format(self._report_timestep, new_report)
                logger.warning(msg)
                warnings.warn(msg)
                self._report_timestep = new_report

        if solver_options is None:
            self._solver_options = dict()
        else:
            self._solver_options = dict(solver_options)
        if backup_solver_options is None:
            self._backup_solver_options = dict()
        else:
            self._backup_solver_options = dict(backup_solver_options)

        self._solver = solver
        self._backup_solver = backup_solver

        if self._solver is scipy.optimize.fsolve:
            self._solver_options.pop('fprime', False)
            self._solver_options['full_output'] = True
            use_jac = self._solver_options.pop('use_jac', False)
            if use_jac:
                dense_jac = _DenseJac(self._model)
                self._solver_options['fprime'] = dense_jac.eval

        if self._backup_solver is scipy.optimize.fsolve:
            self._backup_solver_options.pop('fprime', False)
            self._backup_solver_options['full_output'] = True
            use_jac = self._backup_solver_options.pop('use_jac', False)
            if use_jac:
                dense_jac = _DenseJac(self._model)
                self._backup_solver_options['fprime'] = dense_jac.eval

        self._convergence_error = convergence_error

    def _get_all_tank_controls(self):

        tank_controls = []

        for tank_name, tank in self._wn.nodes(Tank):

            # add the tank controls
            all_links = self._wn.get_links_for_node(tank_name, 'ALL')

            # First take care of the min level
            min_head = tank.min_level + tank.elevation
            for link_name in all_links:
                link = self._wn.get_link(link_name)
                link_has_cv = False  # flow leaving the tank (start node = tank)
                if isinstance(link, Pipe):
                    if link.check_valve:
                        if link.end_node_name == tank_name:
                            continue
                        else:
                            link_has_cv = True
                elif isinstance(link, Pump):
                    if link.end_node_name == tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Closed, 'status')
                open_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Open, 'status')

                close_condition = ValueCondition(tank, 'head', Comparison.le, min_head)
                close_control_1 = Control(condition=close_condition, then_action=close_control_action,
                                          priority=ControlPriority.medium)
                close_control_1._control_type = _ControlType.pre_and_postsolve
                tank_controls.append(close_control_1)

                if not link_has_cv:
                    open_condition_1 = ValueCondition(tank, 'head', Comparison.ge, min_head + self._Htol)
                    open_control_1 = Control(condition=open_condition_1, then_action=open_control_action,
                                             priority=ControlPriority.low)
                    open_control_1._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_1)

                    if link.start_node is tank:
                        other_node = link.end_node
                    elif link.end_node is tank:
                        other_node = link.start_node
                    else:
                        raise RuntimeError('Tank is neither the start node nore the end node.')
                    open_condition_2a = RelativeCondition(tank, 'head', Comparison.le, other_node, 'head')
                    open_condition_2b = ValueCondition(tank, 'head', Comparison.le, min_head + self._Htol)
                    open_condition_2 = AndCondition(open_condition_2a, open_condition_2b)
                    open_control_2 = Control(condition=open_condition_2, then_action=open_control_action,
                                             priority=ControlPriority.high)
                    open_control_2._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_2)

            # Now take care of the max level
            max_head = tank.max_level + tank.elevation
            for link_name in all_links:
                link = self._wn.get_link(link_name)
                link_has_cv = False  # flow entering the tank (end node = tank)
                if isinstance(link, Pipe):
                    if link.check_valve:
                        if link.start_node_name == tank_name:
                            continue
                        else:
                            link_has_cv = True
                if isinstance(link, Pump):
                    if link.start_node_name == tank_name:
                        continue
                    else:
                        link_has_cv = True

                close_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Closed, 'status')
                open_control_action = _InternalControlAction(link, '_internal_status', LinkStatus.Open, 'status')

                close_condition = ValueCondition(tank, 'head', Comparison.ge, max_head)
                close_control = Control(condition=close_condition, then_action=close_control_action,
                                        priority=ControlPriority.medium)
                close_control._control_type = _ControlType.pre_and_postsolve
                tank_controls.append(close_control)

                if not link_has_cv:
                    open_condition_1 = ValueCondition(tank, 'head', Comparison.le, max_head - self._Htol)
                    open_control_1 = Control(condition=open_condition_1, then_action=open_control_action,
                                             priority=ControlPriority.low)
                    open_control_1._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_1)

                    if link.start_node is tank:
                        other_node = link.end_node
                    elif link.end_node is tank:
                        other_node = link.start_node
                    else:
                        raise RuntimeError('Tank is neither the start node nore the end node.')
                    open_condition_2a = RelativeCondition(tank, 'head', Comparison.ge, other_node, 'head')
                    open_condition_2b = ValueCondition(tank, 'head', Comparison.ge, max_head - self._Htol)
                    open_condition_2 = AndCondition(open_condition_2a, open_condition_2b)
                    open_control_2 = Control(condition=open_condition_2, then_action=open_control_action,
                                             priority=ControlPriority.high)
                    open_control_2._control_type = _ControlType.postsolve
                    tank_controls.append(open_control_2)

        return tank_controls

    def _get_cv_controls(self):
        cv_controls = []
        for pipe_name, pipe in self._wn.pipes():
            if pipe.check_valve:
                pipe = self._wn.get_link(pipe_name)
                open_condition = _OpenCVCondition(self._wn, pipe)
                close_condition = _CloseCVCondition(self._wn, pipe)
                open_action = _InternalControlAction(pipe, '_internal_status', LinkStatus.Open, 'status')
                close_action = _InternalControlAction(pipe, '_internal_status', LinkStatus.Closed, 'status')
                open_control = Control(condition=open_condition, then_action=open_action, priority=ControlPriority.very_low)
                close_control = Control(condition=close_condition, then_action=close_action,
                                        priority=ControlPriority.very_high)
                open_control._control_type = _ControlType.postsolve
                close_control._control_type = _ControlType.postsolve
                cv_controls.append(open_control)
                cv_controls.append(close_control)

        return cv_controls

    def _get_pump_controls(self):
        pump_controls = []

        for control_name, control in self._wn.controls():
            for action in control.actions():
                target_obj, target_attr = action.target()
                if target_attr == 'base_speed':
                    if not isinstance(target_obj, Pump):
                        raise ValueError('base_speed can only be changed on pumps; ' + str(control))
                    new_status = LinkStatus.Open
                    new_action = ControlAction(target_obj, 'status', new_status)
                    condition = control.condition
                    new_control = type(control)(condition, new_action, priority=control.priority)
                    pump_controls.append(new_control)

        for pump_name, pump in self._wn.pumps():
            close_control_action = _InternalControlAction(pump, '_internal_status', LinkStatus.Closed, 'status')
            open_control_action = _InternalControlAction(pump, '_internal_status', LinkStatus.Open, 'status')

            if pump.pump_type == 'HEAD':
                close_condition = _CloseHeadPumpCondition(self._wn, pump)
                open_condition = _OpenHeadPumpCondition(self._wn, pump)
            elif pump.pump_type == 'POWER':
                close_condition = _ClosePowerPumpCondition(self._wn, pump)
                open_condition = _OpenPowerPumpCondition(self._wn, pump)
            else:
                raise ValueError('Unrecognized pump pump_type: {0}'.format(pump.pump_type))

            close_control = Control(condition=close_condition, then_action=close_control_action,
                                    priority=ControlPriority.very_high)
            open_control = Control(condition=open_condition, then_action=open_control_action,
                                   priority=ControlPriority.very_low)

            close_control._control_type = _ControlType.postsolve
            open_control._control_type = _ControlType.postsolve

            pump_controls.append(close_control)
            pump_controls.append(open_control)

        return pump_controls

    def _get_valve_controls(self):
        valve_controls = []

        for control_name, control in self._wn.controls():
            for action in control.actions():
                target_obj, target_attr = action.target()
                if target_attr == 'setting':
                    if isinstance(target_obj, Valve):
                        new_status = LinkStatus.Active
                    elif isinstance(target_obj, Pump):
                        raise ValueError('Cannot control settings on pumps; use "base_speed"; ' + str(control))
                    else:
                        raise ValueError('Settings can only be changed on valves: ' + str(control))
                    new_action = ControlAction(target_obj, 'status', new_status)
                    condition = control.condition
                    new_control = type(control)(condition, new_action, priority=control.priority)
                    valve_controls.append(new_control)

        for valve_name, valve in self._wn.valves():

            if valve.valve_type == 'PRV':
                close_condition = _ClosePRVCondition(self._wn, valve)
                open_condition = _OpenPRVCondition(self._wn, valve)
                active_condition = _ActivePRVCondition(self._wn, valve)
                close_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Closed, 'status')
                open_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                active_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Active, 'status')
                close_control = Control(condition=close_condition, then_action=close_action,
                                        priority=ControlPriority.very_high)
                open_control = Control(condition=open_condition, then_action=open_action,
                                       priority=ControlPriority.very_low)
                active_control = Control(condition=active_condition, then_action=active_action,
                                         priority=ControlPriority.very_low)
                close_control._control_type = _ControlType.postsolve
                open_control._control_type = _ControlType.postsolve
                active_control._control_type = _ControlType.postsolve
                valve_controls.append(close_control)
                valve_controls.append(open_control)
                valve_controls.append(active_control)

            elif valve.valve_type == 'PSV':
                close_condition = _ClosePSVCondition(self._wn, valve)
                open_condition = _OpenPSVCondition(self._wn, valve)
                active_condition = _ActivePSVCondition(self._wn, valve)
                close_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Closed, 'status')
                open_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                active_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Active, 'status')
                close_control = Control(condition=close_condition, then_action=close_action,
                                        priority=ControlPriority.very_high)
                open_control = Control(condition=open_condition, then_action=open_action,
                                       priority=ControlPriority.very_low)
                active_control = Control(condition=active_condition, then_action=active_action,
                                         priority=ControlPriority.very_low)
                close_control._control_type = _ControlType.postsolve
                open_control._control_type = _ControlType.postsolve
                active_control._control_type = _ControlType.postsolve
                valve_controls.append(close_control)
                valve_controls.append(open_control)
                valve_controls.append(active_control)

            elif valve.valve_type == 'FCV':
                open_condition = _OpenFCVCondition(self._wn, valve)
                active_condition = _ActiveFCVCondition(self._wn, valve)
                open_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                active_action = _InternalControlAction(valve, '_internal_status', LinkStatus.Active, 'status')
                open_control = Control(condition=open_condition, then_action=open_action,
                                       priority=ControlPriority.very_low)
                active_control = Control(condition=active_condition, then_action=active_action,
                                         priority=ControlPriority.very_low)
                open_control._control_type = _ControlType.postsolve
                active_control._control_type = _ControlType.postsolve
                valve_controls.append(open_control)
                valve_controls.append(active_control)

            if valve.valve_type in {'PSV', 'PRV', 'FCV'}:
                active_condition = ValueCondition(source_obj=valve, source_attr='status', relation=Comparison.eq,
                                                  threshold=LinkStatus.Active)
                upstream_source_condition = FunctionCondition(self._valve_source_checker.should_valve_be_opened,
                                                              func_kwargs={'valve': valve},
                                                              requires=[valve])
                condition = AndCondition(cond1=active_condition, cond2=upstream_source_condition)
                action = _InternalControlAction(valve, '_internal_status', LinkStatus.Open, 'status')
                control = Control(condition=condition, then_action=action, priority=ControlPriority.very_high)
                control._control_type = _ControlType.feasibility
                valve_controls.append(control)

        return valve_controls

    def _register_controls_with_observers(self):
        for mgr in [self._presolve_controls, self._postsolve_controls, self._rules, self._feasibility_controls]:
            for control in mgr._controls:
                self._valve_source_checker.register_control(control)
                self._change_tracker.register_control(control)

    def _get_control_managers(self):
        self._presolve_controls = ControlChecker()
        self._postsolve_controls = ControlChecker()
        self._rules = ControlChecker()
        self._feasibility_controls = ControlChecker()
        self._change_tracker = ControlChangeTracker()

        def categorize_control(control):
            if control.epanet_control_type in {_ControlType.presolve, _ControlType.pre_and_postsolve}:
                self._presolve_controls.register_control(control)
            if control.epanet_control_type in {_ControlType.postsolve, _ControlType.pre_and_postsolve}:
                self._postsolve_controls.register_control(control)
            if control.epanet_control_type == _ControlType.rule:
                self._rules.register_control(control)
            if control.epanet_control_type == _ControlType.feasibility:
                self._feasibility_controls.register_control(control)

        for c_name, c in self._wn.controls():
            categorize_control(c)
        for c in self._get_all_tank_controls():
            categorize_control(c)
        for c in self._get_cv_controls():
            categorize_control(c)
        for c in self._get_pump_controls():
            categorize_control(c)
        for c in self._get_valve_controls():
            categorize_control(c)

        if logger.getEffectiveLevel() <= 1:
            logger.log(1, 'collected presolve controls:')
            for c in self._presolve_controls:
                logger.log(1, '\t' + str(c))
            logger.log(1, 'collected rules:')
            for c in self._rules:
                logger.log(1, '\t' + str(c))
            logger.log(1, 'collected postsolve controls:')
            for c in self._postsolve_controls:
                logger.log(1, '\t' + str(c))
            logger.log(1, 'collected feasibility controls:')
            for c in self._feasibility_controls:
                logger.log(1, '\t' + str(c))

    def _compute_next_timestep_and_run_presolve_controls_and_rules(self, first_step):
        """
        1) Determine the next time step. This depends on both presolve controls and rules. Note that
           (unless this is the first time step) the current value of wn.sim_time is the next hydraulic
           timestep. If there are presolve controls or rules that need activated before the next hydraulic
           timestep, then the wn.sim_time will be adjusted within this if statement.

            a) check the presolve controls to see which ones need activated.
            b) if there is a presolve control(s) that need activated and it needs activated at a time
               that is earlier than the next rule timestep, then the next simulation time is determined
               by that presolve controls
            c) if there are any rules that need activated before the next hydraulic timestep, then
               wn.sim_time will be adjusted to the appropriate rule timestep.
        2) Activate the appropriate controls
        """
        self._change_tracker.set_reference_point('presolve')

        # check which presolve controls need to be activated before the next hydraulic timestep
        presolve_controls_to_run = self._presolve_controls.check()
        presolve_controls_to_run.sort(key=lambda i: i[0]._priority)  # sort them by priority
        # now sort them from largest to smallest "backtrack"; this way they are in the time-order
        # in which they need to be activated
        presolve_controls_to_run.sort(key=lambda i: i[1], reverse=True)
        if first_step:  # we don't want to backtrack if the sim time is 0
            presolve_controls_to_run = [(c, 0) for c, b in presolve_controls_to_run]
        if logger.getEffectiveLevel() <= 1:
            logger.log(1, 'presolve_controls that need activated before the next hydraulic timestep:')
            for pctr in presolve_controls_to_run:
                logger.log(1, '\tcontrol: {0} \tbacktrack: {1}'.format(pctr[0], pctr[1]))
        cnt = 0

        # loop until we have checked all of the presolve_controls_to_run and all of the rules prior to the next
        # hydraulic timestep
        while cnt < len(presolve_controls_to_run) or self._rule_iter * self._wn.options.time.rule_timestep <= self._wn.sim_time:
            if cnt >= len(presolve_controls_to_run):
                # We have already checked all of the presolve_controls_to_run, and nothing changed
                # Now we just need to check the rules
                if logger.getEffectiveLevel() <= 1:
                    logger.log(1, 'no presolve controls need activated; checking rules at rule timestep {0}'.format(
                        self._rule_iter * self._wn.options.time.rule_timestep))
                old_time = self._wn.sim_time
                self._wn.sim_time = self._rule_iter * self._wn.options.time.rule_timestep
                if not first_step:
                    wntr.sim.hydraulics.update_tank_heads(self._wn)
                self._rule_iter += 1
                rules_to_run = self._rules.check()
                rules_to_run.sort(key=lambda i: i[0]._priority)
                for rule, rule_back in rules_to_run:  # rule_back is the "backtrack" which is not actually used for rules
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, '\tactivating rule {0}'.format(rule))
                    rule.run_control_action()
                if self._change_tracker.changes_made(ref_point='presolve'):
                    # If changes were made, then we found the next timestep; break
                    break
                # if no changes were made, then set the wn.sim_time back
                if logger.getEffectiveLevel() <= 1:
                    logger.log(1, 'no changes made by rules at rule timestep {0}'.format(
                        (self._rule_iter - 1) * self._wn.options.time.rule_timestep))
                self._wn.sim_time = old_time
            else:
                # check the next presolve control in presolve_controls_to_run
                control, backtrack = presolve_controls_to_run[cnt]
                if logger.getEffectiveLevel() <= 1:
                    logger.log(1, 'checking control {0}; backtrack: {1}'.format(control, backtrack))
                if self._wn.sim_time - backtrack < self._rule_iter * self._wn.options.time.rule_timestep:
                    # The control needs activated before the next rule timestep; Activate the control and
                    # any controls with the samve value for backtrack
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, 'control {0} needs run before the next rule timestep.'.format(control))
                    control.run_control_action()
                    cnt += 1
                    while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                        # Also activate all of the controls that have the same value for backtrack
                        if logger.getEffectiveLevel() <= 1:
                            logger.log(1, '\talso activating control {0}; backtrack: {1}'.format(
                                presolve_controls_to_run[cnt][0],
                                presolve_controls_to_run[cnt][1]))
                        presolve_controls_to_run[cnt][0].run_control_action()
                        cnt += 1
                    if self._change_tracker.changes_made(ref_point='presolve'):
                        # changes were actually made; we found the next timestep; update wn.sim_time and break
                        self._wn.sim_time -= backtrack
                        break
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, 'controls with backtrack {0} did not make any changes'.format(backtrack))
                elif self._wn.sim_time - backtrack == self._rule_iter * self._wn.options.time.rule_timestep:
                    # the control needs activated at the same time as the next rule timestep;
                    # activate the control, any controls with the same value for backtrack, and any rules at
                    # this rule timestep
                    # the rules need run first (I think to match epanet)
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, 'control has backtrack equivalent to next rule timestep')
                    self._rule_iter += 1
                    self._wn.sim_time -= backtrack
                    if not first_step:
                        wntr.sim.hydraulics.update_tank_heads(self._wn)
                    rules_to_run = self._rules.check()
                    rules_to_run.sort(key=lambda i: i[0]._priority)
                    for rule, rule_back in rules_to_run:
                        if logger.getEffectiveLevel() <= 1:
                            logger.log(1, '\tactivating rule {0}'.format(rule))
                        rule.run_control_action()
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, '\tactivating control {0}; backtrack: {1}'.format(control, backtrack))
                    control.run_control_action()
                    cnt += 1
                    while cnt < len(presolve_controls_to_run) and presolve_controls_to_run[cnt][1] == backtrack:
                        if logger.getEffectiveLevel() <= 1:
                            logger.log(1, '\talso activating control {0}; backtrack: {1}'.format(
                                presolve_controls_to_run[cnt][0], presolve_controls_to_run[cnt][1]))
                        presolve_controls_to_run[cnt][0].run_control_action()
                        cnt += 1
                    if self._change_tracker.changes_made(ref_point='presolve'):
                        break
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1,
                                   'no changes made by presolve controls or rules at backtrack {0}'.format(backtrack))
                    self._wn.sim_time += backtrack
                else:
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, 'The next rule timestep is before this control needs activated; checking rules')
                    old_time = self._wn.sim_time
                    self._wn.sim_time = self._rule_iter * self._wn.options.time.rule_timestep
                    self._rule_iter += 1
                    if not first_step:
                        wntr.sim.hydraulics.update_tank_heads(self._wn)
                    rules_to_run = self._rules.check()
                    rules_to_run.sort(key=lambda i: i[0]._priority)
                    for rule, rule_back in rules_to_run:
                        if logger.getEffectiveLevel() <= 1:
                            logger.log(1, '\tactivating rule {0}'.format(rule))
                        rule.run_control_action()
                    if self._change_tracker.changes_made(ref_point='presolve'):
                        break
                    if logger.getEffectiveLevel() <= 1:
                        logger.log(1, 'no changes made by rules at rule timestep {0}'.format(
                            (self._rule_iter - 1) * self._wn.options.time.rule_timestep))
                    self._wn.sim_time = old_time
        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.debug('changes made by presolve controls and/or rules: ')
            for obj, attr in self._change_tracker.get_changes(ref_point='presolve'):
                logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
        self._change_tracker.remove_reference_point(key='presolve')

    def _run_feasibility_controls(self):
        self._change_tracker.set_reference_point('feasibility')
        feasibility_controls_to_run = self._feasibility_controls.check()
        feasibility_controls_to_run.sort(key=lambda i: i[0]._priority)
        for c, b in feasibility_controls_to_run:
            assert b == 0
            c.run_control_action()
        logger.debug('changes made by feasibility controls:')
        for obj, attr in self._change_tracker.get_changes(ref_point='feasibility'):
            logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
        self._change_tracker.remove_reference_point(key='feasibility')

    def _run_postsolve_controls(self):
        self._change_tracker.set_reference_point('postsolve')
        logger.debug('checking postsolve controls')
        postsolve_controls_to_run = self._postsolve_controls.check()
        postsolve_controls_to_run.sort(key=lambda i: i[0]._priority)
        for control, unused in postsolve_controls_to_run:
            if logger.getEffectiveLevel() <= 1:
                logger.log(1, '\tactivating control {0}'.format(control))
            control.run_control_action()
        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.debug('postsolve controls made changes:')
            for obj, attr in self._change_tracker.get_changes(ref_point='postsolve'):
                logger.debug('\t{0}.{1} changed to {2}'.format(obj, attr, getattr(obj, attr)))
        self._change_tracker.remove_reference_point('postsolve')

    def run_sim(self, solver=NewtonSolver, backup_solver=None, solver_options=None,
                backup_solver_options=None, convergence_error=False, HW_approx='default',
                diagnostics=False):

        """
        Run an extended period simulation (hydraulics only).

        Parameters
        ----------
        solver: object
            wntr.sim.solvers.NewtonSolver or Scipy solver
        backup_solver: object
            wntr.sim.solvers.NewtonSolver or Scipy solver
        solver_options: dict
            Solver options are specified using the following dictionary keys:

            * MAXITER: the maximum number of iterations for each hydraulic solve (each timestep and trial) (default = 3000)
            * TOL: tolerance for the hydraulic equations (default = 1e-6)
            * BT_RHO: the fraction by which the step length is reduced at each iteration of the line search (default = 0.5)
            * BT_MAXITER: the maximum number of iterations for each line search (default = 100)
            * BACKTRACKING: whether or not to use a line search (default = True)
            * BT_START_ITER: the newton iteration at which a line search should start being used (default = 2)
            * THREADS: the number of threads to use in constraint and jacobian computations
        backup_solver_options: dict
        convergence_error: bool (optional)
            If convergence_error is True, an error will be raised if the
            simulation does not converge. If convergence_error is False, partial results are returned, 
            a warning will be issued, and results.error_code will be set to 0
            if the simulation does not converge.  Default = False.
        HW_approx: str
            Specifies which Hazen-Williams headloss approximation to use. Options are 'default' and 'piecewise'. Please
            see the WNTR documentation on hydraulics for details.
        diagnostics: bool
            If True, then run with diagnostics on
        """
        logger.debug('creating hydraulic model')
        self.mode = self._wn.options.hydraulic.demand_model
        self._model, self._model_updater = wntr.sim.hydraulics.create_hydraulic_model(wn=self._wn, HW_approx=HW_approx)

        if diagnostics:
            diagnostics = _Diagnostics(self._wn, self._model, self.mode, enable=True)
        else:
            diagnostics = _Diagnostics(self._wn, self._model, self.mode, enable=False)

        self._setup_sim_options(solver=solver, backup_solver=backup_solver, solver_options=solver_options,
                                backup_solver_options=backup_solver_options, convergence_error=convergence_error)

        self._valve_source_checker = _ValveSourceChecker(self._wn)
        self._get_control_managers()
        self._register_controls_with_observers()

        node_res, link_res = wntr.sim.hydraulics.initialize_results_dict(self._wn)
        results = wntr.sim.results.SimulationResults()
        results.error_code = None
        results.time = []
        results.network_name = self._wn.name

        self._initialize_internal_graph()
        self._change_tracker.set_reference_point('graph')
        self._change_tracker.set_reference_point('model')

        if self._wn.sim_time == 0:
            first_step = True
        else:
            first_step = False
        trial = -1
        max_trials = self._wn.options.hydraulic.trials
        resolve = False
        self._rule_iter = 0  # this is used to determine the rule timestep

        if first_step:
            wntr.sim.hydraulics.update_network_previous_values(self._wn)
            self._wn._prev_sim_time = -1

        logger.debug('starting simulation')

        logger.info('{0:<10}{1:<10}{2:<10}{3:<15}{4:<15}'.format('Sim Time', 'Trial', 'Solver', '# isolated', '# isolated'))
        logger.info('{0:<10}{1:<10}{2:<10}{3:<15}{4:<15}'.format('', '', '# iter', 'junctions', 'links'))
        while True:
            if logger.getEffectiveLevel() <= logging.DEBUG:
                logger.debug('\n\n')

            if not resolve:
                if not first_step:
                    """
                    The tank levels/heads must be done before checking the controls because the TankLevelControls
                    depend on the tank levels. These will be updated again after we determine the next actual timestep.
                    """
                    wntr.sim.hydraulics.update_tank_heads(self._wn)
                trial = 0
                self._compute_next_timestep_and_run_presolve_controls_and_rules(first_step)

            self._run_feasibility_controls()

            # Prepare for solve
            self._update_internal_graph()
            num_isolated_junctions, num_isolated_links = self._get_isolated_junctions_and_links()
            if not first_step and not resolve:
                wntr.sim.hydraulics.update_tank_heads(self._wn)
            wntr.sim.hydraulics.update_model_for_controls(self._model, self._wn, self._model_updater, self._change_tracker)
            wntr.sim.models.param.source_head_param(self._model, self._wn)
            wntr.sim.models.param.expected_demand_param(self._model, self._wn)

            diagnostics.run(last_step='presolve controls, rules, and model updates', next_step='solve')

            solver_status, mesg, iter_count = _solver_helper(self._model, self._solver, self._solver_options)
            if solver_status == 0 and self._backup_solver is not None:
                solver_status, mesg, iter_count = _solver_helper(self._model, self._backup_solver, self._backup_solver_options)
            if solver_status == 0:
                if self._convergence_error:
                    logger.error('Simulation did not converge at time ' + self._get_time() + '. ' + mesg) 
                    raise RuntimeError('Simulation did not converge at time ' + self._get_time() + '. ' + mesg)
                warnings.warn('Simulation did not converge at time ' + self._get_time() + '. ' + mesg)
                logger.warning('Simulation did not converge at time ' + self._get_time() + '. ' + mesg)
                results.error_code = wntr.sim.results.ResultsStatus.error
                diagnostics.run(last_step='solve', next_step='break')
                break

            logger.info('{0:<10}{1:<10}{2:<10}{3:<15}{4:<15}'.format(self._get_time(), trial, iter_count, num_isolated_junctions, num_isolated_links))

            # Enter results in network and update previous inputs
            logger.debug('storing results in network')
            wntr.sim.hydraulics.store_results_in_network(self._wn, self._model)

            diagnostics.run(last_step='solve and store results in network', next_step='postsolve controls')

            self._run_postsolve_controls()
            self._run_feasibility_controls()
            if self._change_tracker.changes_made(ref_point='graph'):
                resolve = True
                self._update_internal_graph()
                wntr.sim.hydraulics.update_model_for_controls(self._model, self._wn, self._model_updater, self._change_tracker)
                diagnostics.run(last_step='postsolve controls and model updates', next_step='solve next trial')
                trial += 1
                if trial > max_trials:
                    if convergence_error:
                        logger.error('Exceeded maximum number of trials at time ' + self._get_time() + '. ') 
                        raise RuntimeError('Exceeded maximum number of trials at time ' + self._get_time() + '. ' ) 
                    results.error_code = wntr.sim.results.ResultsStatus.error
                    warnings.warn('Exceeded maximum number of trials at time ' + self._get_time() + '. ') 
                    logger.warning('Exceeded maximum number of trials at time ' + self._get_time() + '. ' ) 
                    break
                continue

            diagnostics.run(last_step='postsolve controls and model updates', next_step='advance time')

            logger.debug('no changes made by postsolve controls; moving to next timestep')

            resolve = False
            if type(self._report_timestep) == float or type(self._report_timestep) == int:
                if self._wn.sim_time % self._report_timestep == 0:
                    wntr.sim.hydraulics.save_results(self._wn, node_res, link_res)
                    if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                        if int(self._wn.sim_time) != self._wn.sim_time:
                            raise RuntimeError('Time steps increments smaller than 1 second are forbidden.'+
                                               ' Keep time steps as an integer number of seconds.')
                        else:
                            raise RuntimeError('Simulation already solved this timestep')
                    results.time.append(int(self._wn.sim_time))
            elif self._report_timestep.upper() == 'ALL':
                wntr.sim.hydraulics.save_results(self._wn, node_res, link_res)
                if len(results.time) > 0 and int(self._wn.sim_time) == results.time[-1]:
                    raise RuntimeError('Simulation already solved this timestep')
                results.time.append(int(self._wn.sim_time))
            wntr.sim.hydraulics.update_network_previous_values(self._wn)
            first_step = False
            self._wn.sim_time += self._hydraulic_timestep
            overstep = float(self._wn.sim_time) % self._hydraulic_timestep
            self._wn.sim_time -= overstep

            if self._wn.sim_time > self._wn.options.time.duration:
                break

        wntr.sim.hydraulics.get_results(self._wn, results, node_res, link_res)
        
        return results

    def _initialize_name_id_maps(self):
        n = 0
        for link_name, link in self._wn.links():
            self._link_name_to_id[link_name] = n
            self._link_id_to_name[n] = link_name
            n += 1
        n = 0
        for node_name, node in self._wn.nodes():
            self._node_name_to_id[node_name] = n
            self._node_id_to_name[n] = node_name
            n += 1

    def _initialize_internal_graph(self):
        n_links = OrderedDict()
        rows = []
        cols = []
        vals = []
        for link_name, link in itertools.chain(self._wn.pipes(), self._wn.pumps(), self._wn.valves()):
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._node_name_to_id[from_node_name]
            to_node_id = self._node_name_to_id[to_node_name]
            if (from_node_id, to_node_id) not in n_links:
                n_links[(from_node_id, to_node_id)] = 0
                n_links[(to_node_id, from_node_id)] = 0
            n_links[(from_node_id, to_node_id)] += 1
            n_links[(to_node_id, from_node_id)] += 1
            rows.append(from_node_id)
            cols.append(to_node_id)
            rows.append(to_node_id)
            cols.append(from_node_id)
            if link.status == wntr.network.LinkStatus.Closed:
                vals.append(0)
                vals.append(0)
            else:
                vals.append(1)
                vals.append(1)

        rows = np.array(rows, dtype=self._int_dtype)
        cols = np.array(cols, dtype=self._int_dtype)
        vals = np.array(vals, dtype=self._int_dtype)
        self._internal_graph = scipy.sparse.csr_matrix((vals, (rows, cols)))

        ndx_map = OrderedDict()
        for link_name, link in self._wn.links():
            from_node_name = link.start_node_name
            to_node_name = link.end_node_name
            from_node_id = self._node_name_to_id[from_node_name]
            to_node_id = self._node_name_to_id[to_node_name]
            ndx1 = _get_csr_data_index(self._internal_graph, from_node_id, to_node_id)
            ndx2 = _get_csr_data_index(self._internal_graph, to_node_id, from_node_id)
            ndx_map[link] = (ndx1, ndx2)
        self._map_link_to_internal_graph_data_ndx = ndx_map

        self._number_of_connections = [0 for i in range(self._wn.num_nodes)]
        for node_id in self._node_id_to_name.keys():
            self._number_of_connections[node_id] = self._internal_graph.indptr[node_id+1] - self._internal_graph.indptr[node_id]
        self._number_of_connections = np.array(self._number_of_connections, dtype=self._int_dtype)

        self._node_pairs_with_multiple_links = OrderedDict()
        for from_node_id, to_node_id in n_links.keys():
            if n_links[(from_node_id, to_node_id)] > 1:
                if (to_node_id, from_node_id) in self._node_pairs_with_multiple_links:
                    continue
                self._internal_graph[from_node_id, to_node_id] = 0
                self._internal_graph[to_node_id, from_node_id] = 0
                from_node_name = self._node_id_to_name[from_node_id]
                to_node_name = self._node_id_to_name[to_node_id]
                tmp_list = self._node_pairs_with_multiple_links[(from_node_id, to_node_id)] = []
                for link_name in self._wn.get_links_for_node(from_node_name):
                    link = self._wn.get_link(link_name)
                    if link.start_node_name == to_node_name or link.end_node_name == to_node_name:
                        tmp_list.append(link)
                        if link.status != wntr.network.LinkStatus.Closed:
                            ndx1, ndx2 = ndx_map[link]
                            self._internal_graph.data[ndx1] = 1
                            self._internal_graph.data[ndx2] = 1

        self._source_ids = []
        for node_name, node in self._wn.tanks():
            node_id = self._node_name_to_id[node_name]
            self._source_ids.append(node_id)
        for node_name, node in self._wn.reservoirs():
            node_id = self._node_name_to_id[node_name]
            self._source_ids.append(node_id)
        self._source_ids = np.array(self._source_ids, dtype=self._int_dtype)

    def _update_internal_graph(self):
        data = self._internal_graph.data
        ndx_map = self._map_link_to_internal_graph_data_ndx
        for obj, attr in self._change_tracker.get_changes(ref_point='graph'):
            if 'status' == attr:
                if obj.status == wntr.network.LinkStatus.Closed:
                    ndx1, ndx2 = ndx_map[obj]
                    data[ndx1] = 0
                    data[ndx2] = 0
                else:
                    ndx1, ndx2 = ndx_map[obj]
                    data[ndx1] = 1
                    data[ndx2] = 1

        for key, link_list in self._node_pairs_with_multiple_links.items():
            first_link = link_list[0]
            ndx1, ndx2 = ndx_map[first_link]
            data[ndx1] = 0
            data[ndx2] = 0
            for link in link_list:
                if link.status != wntr.network.LinkStatus.Closed:
                    ndx1, ndx2 = ndx_map[link]
                    data[ndx1] = 1
                    data[ndx2] = 1
        self._change_tracker.reset_reference_point(key='graph')

    def _get_isolated_junctions_and_links(self):
        logger_level = logger.getEffectiveLevel()

        if logger_level <= logging.DEBUG:
            logger.debug('checking for isolated junctions and links')
        for j in self._prev_isolated_junctions:
            junction = self._wn.get_node(j)
            junction._is_isolated = False
        for l in self._prev_isolated_links:
            link = self._wn.get_link(l)
            link._is_isolated = False

        node_indicator = np.ones(self._wn.num_nodes, dtype=self._int_dtype)
        check_for_isolated_junctions(self._source_ids, node_indicator, self._internal_graph.indptr,
                                     self._internal_graph.indices, self._internal_graph.data,
                                     self._number_of_connections)

        isolated_junction_ids = [i for i in range(len(node_indicator)) if node_indicator[i] == 1]
        isolated_junctions = OrderedSet()
        isolated_links = OrderedSet()
        for j_id in isolated_junction_ids:
            j = self._node_id_to_name[j_id]
            junction = self._wn.get_node(j)
            junction._is_isolated = True
            isolated_junctions.add(j)
            connected_links = self._wn.get_links_for_node(j)
            for l in connected_links:
                link = self._wn.get_link(l)
                link._is_isolated = True
                isolated_links.add(l)

        if logger_level <= logging.DEBUG:
            if len(isolated_junctions) > 0 or len(isolated_links) > 0:
                logger.debug('isolated junctions: {0}'.format(isolated_junctions))
                logger.debug('isolated links: {0}'.format(isolated_links))
        wntr.sim.hydraulics.update_model_for_isolated_junctions_and_links(self._model, self._wn, self._model_updater,
                                                                          self._prev_isolated_junctions,
                                                                          self._prev_isolated_links,
                                                                          isolated_junctions, isolated_links)
        self._prev_isolated_junctions = isolated_junctions
        self._prev_isolated_links = isolated_links
        return len(isolated_junctions), len(isolated_links)


def _get_csr_data_index(a, row, col):
    """
    Parameters:
    a: scipy.sparse.csr.csr_matrix
    row: int
    col: int
    """
    row_indptr = a.indptr[row]
    num = a.indptr[row+1] - row_indptr
    cols = a.indices[row_indptr:row_indptr+num]
    n = 0
    for j in cols:
        if j == col:
            return row_indptr + n
        n += 1
    raise RuntimeError('Unable to find csr data index.')


def _solver_helper(model, solver, solver_options):
    """

    Parameters
    ----------
    model: wntr.aml.Model
    solver: class or function
    solver_options: dict

    Returns
    -------
    solver_status: int
    message: str
    """
    logger.debug('solving')
    model.set_structure()
    if solver is NewtonSolver:
        _solver = NewtonSolver(solver_options)
        sol = _solver.solve(model)
    elif solver is scipy.optimize.fsolve:
        x, infodict, ier, mesg = solver(model.evaluate_residuals, model.get_x(), **solver_options)
        if ier != 1:
            sol = SolverStatus.error, mesg, None
        else:
            model.load_var_values_from_x(x)
            sol = SolverStatus.converged, mesg, None
    elif solver in {scipy.optimize.newton_krylov, scipy.optimize.anderson, scipy.optimize.broyden1,
                            scipy.optimize.broyden2, scipy.optimize.excitingmixing, scipy.optimize.linearmixing,
                            scipy.optimize.diagbroyden}:
        try:
            x = solver(model.evaluate_residuals, model.get_x(), **solver_options)
            model.load_var_values_from_x(x)
            sol = SolverStatus.converged, '', None
        except:
            sol = SolverStatus.error, '', None
    else:
        raise ValueError('Solver not recognized.')
    return sol


class _DenseJac(object):
    def __init__(self, model):
        self.model = model

    def eval(self, x):
        return self.model.evaluate_jacobian(x).toarray()
