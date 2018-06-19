import logging
from pynt import task
import sys
import time

sys.path.append('.')
import analysis
import plot
from simulation_settings import SimulationSettings, TopologySelection
from simulation import Simulation

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runSimulation(settings, graph):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.

    Returns:
        Simulation -- Completed simulation object.
    """
    
    simulation = Simulation(settings, graph)
    simulation.runSimulation()
    return simulation


@task()
def run(file='sim.json', out='./out/data.p'):
    """Executes one simulation and analyzes resulting data.

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out {str} -- File name to store output to. (default: {'./out/data.p'})
    """

    settings = SimulationSettings(file)
    graph = settings.topology.generateMinerGraph()
    logging.info("Starting simulation")  # TODO: log simulation settings?
    start = time.time()
    simulation = runSimulation(settings, graph)
    data = simulation.generateData(out)

    # DEBUG
    plot.plotDag(simulation.graph.nodes[0]['miner'])

    logging.info("Simulation time: %f" % (time.time() - start))
    analyze()


@task()
def runMonteCarlo(file='sim.json', out='./out/data.p'):
    """Runs a number of Monte Carlo simulations according to settings loaded from file.

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out {str} -- File name to store output to. (default: {'./out/data.p'})
    """

    settings = SimulationSettings(file)
    if settings.topology_selection == TopologySelection.GENERATE_ONCE:
        single_graph = settings.topology.generateMinerGraph()

    for i in range(0, settings.number_of_executions):
        # TODO: thread
        if settings.topology_selection == TopologySelection.GENERATE_EACH_TIME:
            graph = settings.topology.generateMinerGraph()
        else:
            graph = single_graph.copy()

        simulation = runSimulation(settings, graph)
        # TODO: collate/record output


@task()
def analyze(data='./out/data.p'):
    """Analyze data from file.

    Keyword Arguments:
        data {str} -- Data file name. (default: {'./out/data.p'})
    """

    analysis.analyze(data)



# Sets the default task
__DEFAULT__ = run
