import json
import logging
import networkx as nx
import os
import pickle

from id_bag import IdBag
from json_endec import GraphEncoder
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
    def __init__(self, settings, graph, thread_id=0):
        """Sets up a single run of the simulation with the given settings and graph

        Arguments:
            settings {SimulationSettings} -- Stores all settings for the run.
            graph {networkx.graph} -- Graph object to run the simulation on; should have edge delays.
        """

        self.thread_id = thread_id
        self.tick = -1
        self.all_tx = []
        self.completed = False
        self.json_data = None
        self.next_id = 1  # Starts at 1 because genesis tx is 0.
        self.settings = settings
        self.protocol = settings.protocol
        self.graph = graph
        genesis_tx = transaction.Tx(-1, None, 0)
        self.all_tx.append(genesis_tx)
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
            if self.settings.shouldMakeNewTx(self):
                for node_index in self.graph.nodes:
                    self.graph.nodes[node_index]['miner'].attemptToMakeTx()  # If miner wins PoW lottery, generate a new tx.
            for node_index in self.graph.nodes:
                self.graph.nodes[node_index]['miner'].flushMsgs()

            if self.settings.shouldTerminate(self):
                break

            self.tick += 1
        self.completed = True

    def compileData(self):
        """Condenses transaction histories into one history per id.
        Populates self.json_data with data ready to serialize to JSON:
            graph: The simulation's networkx.graph stripped of simulation objects.
            tx_histories: Map of tx id to condensed history of event tuples.
        (Can only be run after simulation is completed.)
        """

        if not self.completed:
            raise Exception("Cannot generate data on a simulation that has not been run.")

        first_instances = {}  # Maps id to first isse of that id.
        for tx in self.all_tx:
            if tx.id not in first_instances:
                first_instances[tx.id] = tx
            elif tx.id in first_instances and first_instances[tx.id].hash() != tx.hash():
                first_instances[tx.id].history += tx.history  # Append tx history to first instance of tx's.

        for edge_id in self.graph.edges:
            self.graph.edges[edge_id].pop('network_delay', None)

        for node_id in self.graph.nodes:
            self.graph.nodes[node_id].pop('miner', None)
            self.graph.nodes[node_id].pop('pos', None)

        self.json_data = {
            'graph': self.graph,
            'tx_histories': {
                tx_id: [(event.time_stamp, event.miner_id, event.state.name) for event in first_instances[tx_id].history] for tx_id in first_instances
            }
        }

    def writeData(self, fname):
        """Writes data pertaining to the completed simulation to a JSON file.
        (Can only be run after simulation is completed.)

        Arguments:
            fname {str} -- File name to write JSON to.
        """

        if not self.json_data:  # Don't generate data more than once.
            self.compileData()
        dir_name = os.path.dirname(fname)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(fname, 'w') as outfile:
            json.dump(self.json_data, outfile, cls=GraphEncoder)
