import copy
import logging
from pynt import task
import sys
import time
import threading

sys.path.append('.')
import analysis
import plot
from simulation_settings import SimulationSettings, TopologySelection
from simulation import Simulation

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runSimulation(settings, graph,thread_id=0):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.

    Returns:
        Simulation -- Completed simulation object.
    """

    simulation = Simulation(settings, graph,thread_id)
    simulation.runSimulation()
    return simulation


def runThreaded(settings, graph, thread_id, out_dir):
    logging.info("in thread %d" % (thread_id))
    assert out_dir[-1] == '/'
    out_file = "%sdata%d.json" % (out_dir, thread_id)
    simulation = runSimulation(settings, graph,thread_id)
    logging.info("thread %d finished with %d ticks" % (thread_id,simulation.tick))
    logging.info("writing to out file %s" % (out_file))
    simulation.writeData(out_file)


@task()
def run(file='sim.json', out='./out/data.json'):
    """Executes one simulation and analyzes resulting data.

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out {str} -- File name to store output to. (default: {'./out/data.json'})
    """

    settings = SimulationSettings(file)
    graph = settings.topology.generateMinerGraph()
    logging.info("Starting simulation")  # TODO: log simulation settings?
    start = time.time()
    simulation = runSimulation(settings, graph)

    # DEBUG
    plot.plotDag(simulation.graph.nodes[0]['miner'])

    simulation.writeData(out)
    logging.info("Simulation time: %f" % (time.time() - start))


@task()
def runMonteCarlo(file='sim.json', out_dir='./out/'):
    """Runs a number of Monte Carlo simulations according to settings loaded from file.

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out_dir {str} -- Directory name to write output to. (default: {'./out/'})
    """

    settings = SimulationSettings(file)
    if settings.topology_selection == TopologySelection.GENERATE_ONCE:
        single_graph = settings.topology.generateMinerGraph()

    threads = []
    for i in range(0, settings.number_of_executions):
        if settings.topology_selection == TopologySelection.GENERATE_EACH_TIME:
            graph = settings.topology.generateMinerGraph()
        else:
            graph = copy.deepcopy(single_graph) # graph.copy() wasn't deepcopying miner objects attached to nodes.

        thread_settings = copy.deepcopy(settings)
        thread = threading.Thread(target=runThreaded, args=[thread_settings, graph, i, out_dir])
        threads.append(thread)
        thread.start()
        logging.info('Started MC %d' % i)


@task()
def analyze(data):
    pass



# Sets the default task
__DEFAULT__ = run
