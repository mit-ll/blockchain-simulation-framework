import logging
from pynt import task
import sys
import time

sys.path.append('.')
from simulation_settings import SimulationSettings, TopologySelection
from simulation import Simulation

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runSimulation(settings, graph):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.
    """
    simulation = Simulation(settings, graph)
    simulation.runSimulation()
    return 'HELLO'  # TODO: return reports(?)


@task()
def run(file='sim.json'):
    settings = SimulationSettings(file)
    graph = settings.topology.generateMinerGraph()
    logging.info("Starting simulation") # TODO: log simulation settings?
    start = time.time()
    output = runSimulation(settings, graph)
    logging.info("Simulation time: %f" % (time.time() - start))
    # TODO: Record this output


@task()
def runMonteCarlo(file='sim.json'):
    settings = SimulationSettings(file)
    if settings.topology_selection == TopologySelection.GENERATE_ONCE:
        single_graph = settings.topology.generateMinerGraph()

    for i in range(0, settings.number_of_executions):
        # TODO: thread
        if settings.topology_selection == TopologySelection.GENERATE_EACH_TIME:
            graph = settings.topology.generateMinerGraph()
        else:
            graph = single_graph.copy()

        # TODO: collate output
        output = runSimulation(settings, graph)


@task()
def analyze(input='./out/data'):
    # TODO
    pass


# Sets the default task
__DEFAULT__ = run
