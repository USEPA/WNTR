from importlib.resources import files

import wntr


def load_test_network():
    network_path = files("wntr.library").joinpath("networks", "Net1.inp")
    return wntr.network.WaterNetworkModel(str(network_path))


def run_simulation(network, output_prefix):
    simulator = wntr.sim.EpanetSimulator(network)
    return simulator.run_sim(file_prefix=str(output_prefix), convergence_error=True)


def check_setup():
    network = load_test_network()
    print(f"WNTR version: {wntr.__version__}")
    print(f"Loaded Net1: {network.num_nodes} nodes, {network.num_links} links, {network.num_junctions} junctions, {network.num_pipes} pipes, {network.num_pumps} pumps, {network.num_valves} valves, {network.num_tanks} tanks, {network.num_reservoirs} reservoirs")
