from id_bag import IdBag
from tx import Tx


class Simulation:
    def __init__(self, settings, graph):
        """Sets up a single run of the simulation with the given settings and graph

        Arguments:
            settings {SimulationSettings} -- Stores all settings for the run.
            graph {networkx.graph} -- Graph object to run the simulation on; should have edge delays.
        """
        self.tick = -1
        self.all_tx = []
        self.next_id = 1  # Starts at 1 because genesis tx is 0.
        self.settings = settings
        self.protocol = settings.protocol
        self.graph = graph
        genesis_tx = Tx(-1, None, 0)
        for node_index in self.graph.nodes:
            graph.nodes[node_index]['miner'] = settings.protocol.getMinerClass()(node_index, genesis_tx, graph, self)
        self.updateMinerAdjacencies()

    def updateMinerAdjacencies(self):
        """Set miner.adjacencies for each miner. This should be called once at start up for static topologies, and before every step for dynamic.
        """
        for node_index in self.graph.nodes:
            self.graph.nodes[node_index]['miner'].adjacencies = self.graph[node_index]

    def runSimulation(self):
        self.tick = 0
        while True:
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].id_bag.clear()
                self.graph.nodes[node_index]['miner'].step()  # Process messages, and populate reissues.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].checkReissues()  # Add reissues to miner.id_bag.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].postStep()  # If miner wins PoW lottery, generate a new tx.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].flushMsgs()

            if self.settings.shouldTerminate(self):
                break  # TODO: allow messages to finish propogating? still terminate after a set number of ticks?

            self.tick += 1
