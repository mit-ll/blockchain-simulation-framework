import concurrent.futures
import copy
import logging
from pynt import task
import sys
import time

sys.path.append('.')
import analysis
import plot
from simulation_settings import SimulationSettings, TopologySelection
from simulation import Simulation
import transaction

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runOnce(settings, graph, thread_id=0):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.

    Keyword Arguments:
        thread_id {int} -- The thread number of this run of the simulation. (default: {0})

    Returns:
        Simulation -- Completed simulation object.
    """

    simulation = Simulation(settings, graph, thread_id)
    simulation.runSimulation()
    return simulation


def runThreaded(settings, graph, thread_id, out_dir):
    """Runs the simulation once, directing output to a thread-unique file. Intended to be used as the thread's target function.

    Arguments:
        settings {SimulationSettings} -- Stores all settings for the run.
        graph {networkx.Graph} -- Graph object to run the simulation on; should have edge delays.
        thread_id {int} -- The thread number of this run of the simulation.
        out_dir {string} -- The directory where output should be written.
    """

    assert out_dir[-1] == '/'
    logging.debug('Started thread %d' % thread_id)
    out_file = "%sdata%d.json" % (out_dir, thread_id)
    simulation = runOnce(settings, graph, thread_id)
    simulation.writeData(out_file)
    logging.debug('Finished thread %d' % thread_id)


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
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.thread_workers) as executor:
        for thread_id in range(0, settings.number_of_executions):
            if settings.topology_selection == TopologySelection.GENERATE_EACH_TIME:
                graph = settings.topology.generateMinerGraph()
            else:
                graph = copy.deepcopy(single_graph)  # graph.copy() wasn't deepcopying miner objects attached to nodes.
            thread_settings = copy.deepcopy(settings)
            executor.submit(runThreaded, thread_settings, graph, thread_id, out_dir)
    logging.info("Time: %f" % (time.time() - start))


@task()
def run(file='sim.json', out='./out/data.json'):
    """Executes one simulation.

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out {str} -- File name to store output to. (default: {'./out/data.json'})
    """

    settings = SimulationSettings(file)
    graph = settings.topology.generateMinerGraph()
    logging.info("Starting simulation")
    start = time.time()
    simulation = runOnce(settings, graph)

    simulation.writeData(out)
    logging.info("Simulation time: %f" % (time.time() - start))
    # analyze()


@task()
def runWithDebug(file='sim.json', out='./out/data.json'):
    """Executes one simulation and analyzes resulting data, including some debug functions

    Keyword Arguments:
        file {str} -- File name to load settings from. (default: {'sim.json'})
        out {str} -- File name to store output to. (default: {'./out/data.json'})
    """

    settings = SimulationSettings(file)
    graph = settings.topology.generateMinerGraph()
    logging.info("Starting simulation")
    start = time.time()
    simulation = runOnce(settings, graph)

    # DEBUG
    g = simulation.graph
    allMinerIds = set()
    allMiners = []
    for n in g.nodes:
        m = g.nodes[n]['miner']
        allMinerIds.add(m.id)
        allMiners.append(m)
    unconsensed_tx = []  # Consensed by 1 or more but not all miners.
    miners_to_compare = set([0])  # Set of miners to display if some tx are unconsensed (always includes 0 for reference).
    for t in simulation.all_tx:
        states = {}
        for e in t.history:
            states[e.miner_id] = e.state
        s = set([i for i in states if states[i] == transaction.State.CONSENSUS])  # Have to do it like this to capture FINAL state, not just "was this ever in consensus".
        if s and allMinerIds - s:
            miners_to_compare |= set(list(s)[:1])
            unconsensed_tx.append(t)
    if unconsensed_tx:
        print "Consensus has still not been reached for some tx:", [t.id for t in unconsensed_tx]
        print miners_to_compare
        plot.plotAllDags([g.nodes[i]['miner'] for i in miners_to_compare])
    else:
        print "All tx consensed!"
    plot.plotDag(simulation.graph.nodes[0]['miner'])
    # END DEBUG

    simulation.writeData(out)
    logging.info("Simulation time: %f" % (time.time() - start))
    analyze()


@task()
def analyze(data_dir='./out/'):
    """Analyzes the data stored in the given directory.

    Keyword Arguments:
        data_dir {str} -- Path to the directory containing data files. (default: {'./out/'})
    """

    data = analysis.loadData(data_dir)
    # for run in data:
    #    analysis.showMultiCDF(run[1])
    analysis.showTotalCDF(data)
    analysis.reportDisconsensed(data)



# Sets the default task.
__DEFAULT__ = run

if __name__ == "__main__":
    __DEFAULT__()
