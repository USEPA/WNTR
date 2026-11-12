import warnings
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import pandas as pd

import wntr
from wntr.network.controls import BaseControlAction

from .scenario import WaterScenario


def load_test_network():
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")
    return wntr.network.WaterNetworkModel(str(network_path))


def load_ctown(network_path=None):
    if network_path is None:
        network_path = (
            Path(__file__).resolve().parent.parent
            / "examples"
            / "networks"
            / "CTOWN.inp"
        )

    network_path = Path(network_path)

    if not network_path.is_file():
        raise FileNotFoundError(f"CTOWN network file not found: {network_path}")

    return wntr.network.WaterNetworkModel(str(network_path))


def load_preview_network():  # load preset network for prototype dashboard, return a dictionary with the junctions and the network HTML
    network_path = files("wntr.library").joinpath(
        "networks", "Net3.inp"
    )  # loads preset network from WNTR library
    network = wntr.network.WaterNetworkModel(
        str(network_path)
    )  # load the network into a model object
    with (
        TemporaryDirectory() as directory
    ):  # create a temporary directory to store the network HTML file
        plot_path = (
            Path(directory) / "network.html"
        )  # create a path for the network HTML file in the temporary directory
        wntr.graphics.plot_interactive_network(  # asks WNTR to plot the network
            network,
            node_attribute="elevation",  # color nodes by their elevation
            node_attribute_name="Elevation (m)",  # names attribute in the plot's hover details
            filename=str(plot_path),  # tells WNTR where to save the HTML file
            auto_open=False,  # prevents WNTR from opening the HTML file in a browser after saving it
        )
        network_html = plot_path.read_text(
            encoding="utf-8"
        )  # read the HTML file into a string so it can be embedded in the dashboard
    return {  # return a dictionary with junctions and network HTML for the dashboard to use
        "junctions": network.junction_name_list,
        "network_html": network_html,
    }


def run_simulation(network, output_prefix):
    simulator = wntr.sim.EpanetSimulator(network)
    return simulator.run_sim(file_prefix=str(output_prefix), convergence_error=True)


# wrap a normal pump status action so it pauses during the outage
class _PumpStatusAction(BaseControlAction):
    # store original action, simulation model, and outage window
    def __init__(self, action, network, start_time, end_time):
        super().__init__()
        self.action = action
        self.network = network
        self.start_time = start_time
        self.end_time = end_time

    # keep the original action's model dependencies
    def requires(self):
        return self.action.requires()

    # report the same pump and status attribute as the original action
    def target(self):
        return self.action.target()

    # keep the original action's description for logging
    def __str__(self):
        return str(self.action)

    # run the original action outside the outage window and notify the simulator of the update
    def run_control_action(self):
        if not self.start_time < self.network.sim_time <= self.end_time:
            self.action.run_control_action()
            self.notify()


# load requested scenario or default to the bundled pump outage scenario if none is provided
def _load_pump_scenario(scenario_path):
    if scenario_path is None:
        scenario_path = (
            Path(__file__).resolve().parent / "scenarios" / "pump_poweroff_basic.json"
        )
    return WaterScenario.load_from_json(Path(scenario_path))


# check the scenario uses a supported pump outage type and targets one component
def _validate_pump_scenario(scenario):
    if scenario.attack_type not in {"pump_off", "pump_failure"}:
        raise ValueError(
            f"run_pump_attack only supports pump_off/pump_failure scenarios; "
            f"got {scenario.attack_type!r}"
        )
    if len(scenario.target_components) != 1:
        raise ValueError(
            "A pump attack scenario must specify exactly one target component"
        )


# schedule outage, prevent normal controls from reopening the pump mid-outage
def _apply_pump_outage(network, scenario):
    pump_name = scenario.target_components[0]
    if pump_name not in network.pump_name_list:
        raise ValueError(f"Target {pump_name!r} is not a pump in the selected network")

    start_time = scenario.timing.start_time_sec
    end_time = start_time + scenario.timing.duration_sec
    pump = network.get_link(pump_name)

    # wrap only actions that change the selected pump's status
    def guard_pump_status(actions):
        return [
            _PumpStatusAction(action, network, start_time, end_time)
            if action.target() == (pump, "status")
            else action
            for action in actions
        ]

    # apply the guard to matching actions in both branches of each existing control
    for _, control in network.controls():
        if any(action.target() == (pump, "status") for action in control.actions()):
            control.update_then_actions(guard_pump_status(control._then_actions))
            control.update_else_actions(guard_pump_status(control._else_actions))

    pump.add_outage(
        network,
        start_time,
        end_time,
        add_after_outage_rule=True,
    )


def run_pump_attack(
    scenario_path=None,
    network_path=None,
    output_path=None,
):
    """Run one pump outage described by a WNTR-WARD scenario JSON file.

    Provide ``network_path`` to select the EPANET INP file for the scenario's
    ``model_id``. The model ID is descriptive metadata; this function does not
    assume a model filename or maintain a model registry.

    Results are written as one CSV containing node pressures and link
    flowrates at each reported simulation time. The WNTR results object is
    returned for further analysis.
    """
    scenario = _load_pump_scenario(scenario_path)
    if network_path is None:
        raise ValueError("network_path is required to select the scenario model")

    _validate_pump_scenario(scenario)
    network = wntr.network.WaterNetworkModel(str(network_path))
    _apply_pump_outage(network, scenario)
    end_time = scenario.timing.start_time_sec + scenario.timing.duration_sec
    network.options.time.duration = max(network.options.time.duration, end_time)

    simulator = wntr.sim.WNTRSimulator(network)
    results = simulator.run_sim(convergence_error=True)

    if output_path is None:
        output_path = Path.cwd() / f"{scenario.scenario_id}_results.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pressure = results.node["pressure"].add_prefix("node_pressure_")
    flowrate = results.link["flowrate"].add_prefix("link_flowrate_")
    output = pd.concat([pressure, flowrate], axis=1)
    output.index.name = "time_sec"
    output.to_csv(output_path)

    print(f"Simulation results written to: {output_path.resolve()}")
    return results


# run one simulation, collect results, and return a dictionary with the results and metadata
def _run_paired_case(network, scenario=None):
    settings = network.options.to_dict()
    started = perf_counter()
    results = None
    failure = None

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            if scenario is not None:
                _apply_pump_outage(network, scenario)
            results = wntr.sim.WNTRSimulator(network).run_sim(convergence_error=True)
        except (RuntimeError, ValueError, ArithmeticError) as error:
            failure = {"type": type(error).__name__, "message": str(error)}

    return {
        "simulator": "WNTRSimulator",
        "wntr_version": wntr.__version__,
        "settings": settings,
        "elapsed_seconds": perf_counter() - started,
        "converged": results is not None,
        "warnings": [str(warning.message) for warning in caught],
        "failure": failure,
        "node": {}
        if results is None
        else {metric: frame.copy() for metric, frame in results.node.items()},
        "link": {}
        if results is None
        else {metric: frame.copy() for metric, frame in results.link.items()},
    }


# run the baseline and pump outage with matching settings so that the results can be compared
def run_paired_simulations(scenario_path, network_path, *, attack_first=False):
    scenario = _load_pump_scenario(scenario_path)
    _validate_pump_scenario(scenario)
    baseline = wntr.network.WaterNetworkModel(str(network_path))
    attack = wntr.network.WaterNetworkModel(str(network_path))
    end_time = scenario.timing.start_time_sec + scenario.timing.duration_sec
    duration = max(baseline.options.time.duration, end_time)
    baseline.options.time.duration = duration
    attack.options.time.duration = duration

    cases = [("baseline", baseline, None), ("attack", attack, scenario)]
    if attack_first:
        cases.reverse()
    return {name: _run_paired_case(network, outage) for name, network, outage in cases}


def check_setup():
    network = load_test_network()
    print(f"WNTR version: {wntr.__version__}")
    print(
        f"Loaded Net1: {network.num_nodes} nodes, {network.num_links} links, {network.num_junctions} junctions, {network.num_pipes} pipes, {network.num_pumps} pumps, {network.num_valves} valves, {network.num_tanks} tanks, {network.num_reservoirs} reservoirs"
    )
