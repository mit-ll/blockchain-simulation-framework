import logging
from pynt import task
import sys

sys.path.append('.')
from simulation_settings import SimulationSettings, TopologySelection

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runSimulation(settings, graph):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.
    """

    for node in graph.nodes:
        pass
        #graph.nodes[node]['miner'] = settings.protocol.getMinerClass()()

    return None


@task()
def run(file='sim.json'):
    simulation_settings = SimulationSettings(file)
    graph = simulation_settings.topology.generateMinerGraph()
    output = runSimulation(simulation_settings, graph)
    # TODO: Record this output


@task()
def runMonteCarlo(file='sim.json'):
    simulation_settings = SimulationSettings(file)
    if simulation_settings.topology_selection == TopologySelection.GENERATE_ONCE:
        single_graph = simulation_settings.topology.generateMinerGraph()

    for i in range(0, simulation_settings.number_of_executions):
        # thread
        if simulation_settings.topology_selection == TopologySelection.GENERATE_EACH_TIME:
            graph = simulation_settings.topology.generateMinerGraph()
        else:
            graph = single_graph.copy()

        # colate output
        output = runSimulation(simulation_settings, graph)


@task()
def analyze(input='./out/data'):
    # TODO
    pass


# Sets the default task
__DEFAULT__ = run
