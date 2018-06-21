import copy
import logging
from pynt import task
import sys
import time
import threading

sys.path.append('.')
import analysis

import transaction  # DEBUG

import plot
from simulation_settings import SimulationSettings, TopologySelection
from simulation import Simulation

# Setup logging.
logging.basicConfig(level=logging.DEBUG)


def runOnce(settings, graph, thread_id=0):
    """Execute a single run of the simulation.

    Arguments:
        settings {SimulationSettings} -- Settings for the simulation.
        graph {networkx.Graph} -- Graph of the miners.

    Returns:
        Simulation -- Completed simulation object.
    """

    simulation = Simulation(settings, graph, thread_id)
    simulation.runSimulation()
    return simulation


def runThreaded(settings, graph, thread_id, out_dir):
    assert out_dir[-1] == '/'
    out_file = "%sdata%d.json" % (out_dir, thread_id)
    simulation = runOnce(settings, graph, thread_id)
    simulation.writeData(out_file)


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
            graph = copy.deepcopy(single_graph)  # graph.copy() wasn't deepcopying miner objects attached to nodes.

        thread_settings = copy.deepcopy(settings)
        thread = threading.Thread(target=runThreaded, args=[thread_settings, graph, i, out_dir])
        threads.append(thread)
        thread.start()


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
    simulation = runOnce(settings, graph)

    # DEBUG
    g = simulation.graph
    allMinerIds = set()
    allMiners = []
    for n in g.nodes:
        m = g.nodes[n]['miner']
        allMinerIds.add(m.id)
        allMiners.append(m)
    unc = []  # unconsensed tx (consensed by 1 or more but not all miners)
    bad_miners = set([0])  # start with 0 for reference
    for t in simulation.all_tx:
        states = {}
        for e in t.history:
            states[e.miner_id] = e.state
        s = set([i for i in states if states[i] == transaction.State.CONSENSUS])  # have to do it like this to capture FINAL state, not just "was this ever in consensus"
        if s and allMinerIds - s:
            bad_miners |= set(list(s)[:1])
            unc.append(t)
    if unc:
        print "Consensus has still not been reached for some tx:", [t.id for t in unc]
        print bad_miners
        plot.plotAllDags([g.nodes[i]['miner'] for i in bad_miners])
    else:
        print "All tx consensed!"
    plot.plotDag(simulation.graph.nodes[0]['miner'])
    # END DEBUG

    simulation.writeData(out)
    logging.info("Simulation time: %f" % (time.time() - start))


@task()
def analyze(data_dir='./out/'):
    data = analysis.loadData(data_dir)
    for run in data:
        analysis.showMultiCDF(run[1])
    analysis.showTotalCDF(data)



# Sets the default task
__DEFAULT__ = run
