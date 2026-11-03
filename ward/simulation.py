from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

import wntr


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


def check_setup():
    network = load_test_network()
    print(f"WNTR version: {wntr.__version__}")
    print(
        f"Loaded Net1: {network.num_nodes} nodes, {network.num_links} links, {network.num_junctions} junctions, {network.num_pipes} pipes, {network.num_pumps} pumps, {network.num_valves} valves, {network.num_tanks} tanks, {network.num_reservoirs} reservoirs"
    )
