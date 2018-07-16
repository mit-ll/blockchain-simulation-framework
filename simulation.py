import json
import logging
import os
import random

from id_bag import IdBag
from json_endec import GraphEncoder
import transaction


def addToTimes(times, miner_id, time, max_time):
    """Helper function that adds a time to a dictionary mapping miner ids to how long it took that miner to come to consensus on the tx.

    Arguments:
        times {dict} -- Dictionary to add time to.
        miner_id {int} -- Id of miner.
        time {int} -- Time in ticks that it took that miner to come to consensus on the tx.
        max_time {int} -- Current max time for any miner to come to consensus on the tx.

    Returns:
        int -- New max time for any miner to come to consensus on the tx.
    """

    if miner_id not in times:
        times[miner_id] = -99
    if time > times[miner_id]:
        times[miner_id] = time
    if time > max_time:
        max_time = time
    return max_time


def weightedRandomChoice(choices):
    """    
    Arguments:
        choices {list(tuple)} -- List of (choice, weight) tuples.

    Returns:
        any -- One selected choice from choices selected according to a weighted random choice.
    """

    total_weights = sum(weight for choice, weight in choices)
    target = random.uniform(0, total_weights)
    current = 0
    for choice, weight in choices:
        if current + weight >= target:
            return choice
        current += weight
    assert False


class Simulation:
    def __init__(self, settings, graph, thread_id=0):
        """Sets up a single run of the simulation with the given settings and graph

        Arguments:
            settings {SimulationSettings} -- Stores all settings for the run.
            graph {networkx.Graph} -- Graph object to run the simulation on; should have edge delays.

        Keyword Arguments:
            thread_id {int} -- The thread number of this run of the simulation (used for IdBag). (default: {0})
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

        self.attachMiners()

    def attachMiners(self):
        """Creates Miner objects (including calculating power) and attaches them to graph nodes, then populates miner adjacencies.
        """

        top_powers = []
        if self.settings.top_miner_power:
            num_other_miners = len(self.graph.nodes) - len(self.settings.top_miner_power)
            other_miners_power = 100.0 - sum(self.settings.top_miner_power)
            assert num_other_miners > 0 and other_miners_power > 0
            power_to_percent_ratio = float(num_other_miners) / other_miners_power
            top_powers = [percent*power_to_percent_ratio for percent in self.settings.top_miner_power]

        genesis_tx = transaction.Tx(-1, None, 0, [])
        self.all_tx.append(genesis_tx)
        for node_index in self.graph.nodes:
            if node_index > len(top_powers) - 1:
                power = self.settings.miner_power_distribution.sample()
            else:
                power = top_powers[node_index]
            new_miner = self.protocol.getMinerClass()(node_index, genesis_tx, self.graph, self, power)
            self.graph.nodes[node_index]['miner'] = new_miner

        for node_index in self.graph.nodes:
            edges = self.graph[node_index]
            self.graph.nodes[node_index]['miner'].adjacencies = {edge_index: (self.graph.nodes[edge_index]['miner'], edges[edge_index]['network_delay']) for edge_index in edges}

    def runSimulation(self):
        """Run simulation on self.graph according to self.settings.
        """

        if self.completed:  # Don't run the sim more than once.
            return

        miners = []
        miner_choices = []
        for node_index in self.graph.nodes:
            miner = self.graph.nodes[node_index]['miner']
            miners.append(miner)
            miner_choices.append((miner, miner.power))

        generation_probability = 1.0 / self.settings.protocol.target_ticks_between_generation

        self.tick = 0
        changes_since_last_tick = True  # This allows us to skip to tx generation if that's all that needs to be done this tick.
        while True:
            had_changes = changes_since_last_tick
            changes_since_last_tick = False
            if had_changes:
                miners_have_msgs = False
                for miner in miners:
                    if miner.queue:
                        miners_have_msgs = True
                        break
                if miners_have_msgs:
                    changes_since_last_tick = True
                    if self.protocol.isIdBagSingle():
                        miners[0].id_bag.clear()
                    for miner in miners:
                        if not self.protocol.isIdBagSingle():
                            miner.id_bag.clear()
                        miner.handleMsgs()  # Process messages, and populate reissues.
                    for miner in miners:
                        miner.checkReissues()  # Add reissues to miner.id_bag.
            # Global PoW roll is much faster. "While" allows for the event that 2+ miners gen tx on the same tick.
            while self.settings.shouldMakeNewTx(self) and random.random() < generation_probability:
                changes_since_last_tick = True
                weightedRandomChoice(miner_choices).makeNewTx()
            if had_changes or changes_since_last_tick:
                for miner in miners:
                    miner.flushMsgs()

            if self.settings.shouldTerminate(self):
                break

            self.tick += 1
        self.completed = True

    def compileData(self):
        """Condenses transaction histories into one history per id.
        Populates self.json_data with data ready to serialize to JSON:
            graph: The simulation's networkx.Graph stripped of simulation objects.
            tx_histories: Map of tx id to condensed history of event tuples.
        (Can only be run after simulation is completed.)
        """

        if not self.completed:
            raise Exception("Cannot generate data on a simulation that has not been run.")

        if self.json_data:  # Don't generate data more than once.
            return

        first_instances = {}  # Maps id to first isse of that id.
        for tx in self.all_tx:
            if tx.id not in first_instances:
                first_instances[tx.id] = tx
            elif tx.id in first_instances and first_instances[tx.id].hash != tx.hash:
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

        self.compileData()
        dir_name = os.path.dirname(fname)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(fname, 'w') as outfile:
            json.dump(self.json_data, outfile, cls=GraphEncoder)
