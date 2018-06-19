import os
import pickle

from id_bag import IdBag
import transaction


def addToTimes(times, miner_id, time, max_time):
    """Helper function that adds a time to a dictionary mapping miner ids to how long it took that miner to come to consensus on the tx.

    Arguments:
        times {dict} -- Dictionary to add time to.
        miner_id {int} -- Id of miner.
        t {int} -- Time in ticks that it took that miner to come to consensus on the tx.
        mx {int} -- Current max time any miner to come to consensus on the tx.

    Returns:
        int -- New max time any miner to come to consensus on the tx.
    """

    if miner_id not in times:
        times[miner_id] = -99
    if time > times[miner_id]:
        times[miner_id] = time
    if time > max_time:
        max_time = time
    return max_time


class Simulation:
    def __init__(self, settings, graph):
        """Sets up a single run of the simulation with the given settings and graph

        Arguments:
            settings {SimulationSettings} -- Stores all settings for the run.
            graph {networkx.graph} -- Graph object to run the simulation on; should have edge delays.
        """

        self.tick = -1
        self.all_tx = []
        self.completed = False
        self.data = None
        self.next_id = 1  # Starts at 1 because genesis tx is 0.
        self.settings = settings
        self.protocol = settings.protocol
        self.graph = graph
        genesis_tx = transaction.Tx(-1, None, 0)
        for node_index in self.graph.nodes:
            graph.nodes[node_index]['miner'] = settings.protocol.getMinerClass()(node_index, genesis_tx, graph, self)
        self.updateMinerAdjacencies()

    def updateMinerAdjacencies(self):
        """Set miner.adjacencies for each miner. This should be called once at start up for static topologies, and before every step for dynamic.
        """

        for node_index in self.graph.nodes:
            self.graph.nodes[node_index]['miner'].adjacencies = self.graph[node_index]

    def runSimulation(self):
        """Run simulation on self.graph according to self.settings.
        """

        if self.completed:  # Don't run the sim more than once.
            return
        self.tick = 0
        while True:
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].id_bag.clear()
                self.graph.nodes[node_index]['miner'].handleMsgs()  # Process messages, and populate reissues.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].checkReissues()  # Add reissues to miner.id_bag.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].attemptToMakeTx()  # If miner wins PoW lottery, generate a new tx.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].flushMsgs()

            if self.settings.shouldTerminate(self):
                break  # TODO: allow messages to finish propogating? still terminate after a set number of ticks?

            self.tick += 1
        self.completed = True

    def generateData(self, fname=None):
        """Generate data from completed simulation.
        Data includes separating transactions by which were consensed, never consensed, partially consensed, and for which consensus was lost after it was acheived.
        Also includes all_tx which points to every transaction created during the simulation. Transactions with tx.stats can be further analyzed for how long they took to be consensed. 

        Keyword Arguments:
            fname {str} -- Optional file name to write data to. (default: {None})

        Returns:
            dict -- Dictionary of data; see function description for contents.
        """

        if not self.completed:
            raise Exception("Cannot generate data on a simulation that has not been run.")
        if self.data:  # Don't generate data more than once.
            return self.data

        all_miner_ids = set()
        all_miners = []
        for node_index in self.graph.nodes:
            miner = self.graph.nodes[node_index]['miner']
            all_miner_ids.add(miner.id)
            all_miners.append(miner)

        disconsensed_tx = []  # Disconsensed tx (consensed once, then unconsensed) (may overlap with cons, unc, or other).
        partially_consensed_tx = []  # Unconsensed tx (consensed by 1 or more but not all miners).
        consensed_tx = []  # Consensed tx (consensed by all miners) (allTx = cons + unc + other).
        never_consensed_tx = []  # Not consensed by any miner (different from unconsensed).
        first_instances = {}  # Maps id to first isse of that id.
        for tx in self.all_tx:
            if [True for event in tx.history if event.state == transaction.State.DISCONSENSED]:
                disconsensed_tx.append(tx)
            consensus_set = set([event.miner_id for event in tx.history if event.state == transaction.State.CONSENSUS])  # Set of miner ids that consensed on this tx.
            if not consensus_set:
                never_consensed_tx.append(tx)
            elif all_miner_ids - consensus_set:
                partially_consensed_tx.append(tx)
            else:
                consensed_tx.append(tx)
            # Some preprocessing for the probability distribution computation.
            if tx.id not in first_instances:
                first_instances[tx.id] = tx
            if tx.id in first_instances and first_instances[tx.id].hash() != tx.hash():
                first_instances[tx.id].history += tx.history  # Sppend tx history to first instance of tx's.

        # Note: tx with same id are collapsed into the first instance of that id for probability distributions, but not for disconsensed/unconsensed.

        have_seen_first = set()  # Set of tx.ids for which we have handled the first instance (original reissued tx) and will ignore all other tx with that id.
        for tx in self.all_tx:
            if tx.id in have_seen_first:
                continue  # These tx will have tx.stats = {}
            have_seen_first.add(tx.id)
            miner_consensus_times = {}  # Map of miner id to how long that miner took to reach consensus on this tx.
            max_consensus_time = -99
            for event in tx.history:
                if event.state == transaction.State.CONSENSUS:
                    time = event.time_stamp - tx.birthday
                    max_consensus_time = addToTimes(miner_consensus_times, event.miner_id, time, max_consensus_time)
            if max_consensus_time > 0:  # If max is still -99, no tx with that id was ever consensed.
                tx.stats['times'] = miner_consensus_times
                tx.stats['max_time'] = max_consensus_time

        self.data = {
            'disconsensed_tx': disconsensed_tx,
            'partially_consensed_tx': partially_consensed_tx,
            'consensed_tx': consensed_tx,
            'never_consensed_tx': never_consensed_tx,
            'all_tx': self.all_tx
        }
        if fname:
            dir_name = os.path.dirname(fname)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            pickle.dump(self.data, open(fname, 'w+'))  # TODO: serialize JSON instead of pickle.
        return self.data
