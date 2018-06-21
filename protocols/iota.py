import random
import networkx as nx
import transaction
import miner
import bitcoin


class Iota(bitcoin.Bitcoin):
    """Iota protocol miner.
    """

    name = "Iota"

    def __init__(self, miner_id, genesis_tx, graph, simulation):
        """        
        Arguments:
            miner_id {int} -- Miner's id.
            genesis_tx {Tx} -- Blockchain protocol's genesis transaction.
            graph {networkx.Graph} -- Graph of network being simulated.
            simulation {Simulation} -- Simulation object that stores settings and simulation variables.
        """

        bitcoin.Bitcoin.__init__(self, miner_id, genesis_tx, graph, simulation)

    def getNewParents(self):
        """
        Returns:
            list(Tx) -- List of 1 or 2 parent tx for new tx.
        """

        node_choices = list(self.frontier_nodes)
        if self.root in node_choices and len(node_choices) >= 3:
            node_choices.remove(self.root)
        choices = [choice.tx for choice in node_choices]
        num_choices = len(choices)
        assert num_choices > 0
        if num_choices == 2 or choices == [self.root.tx]:
            return choices
        elif num_choices == 1:
            return [choices[0], random.choice([n.tx for n in self.chain_pointers.values() if n.tx not in choices])]  # If there's only one frontier node, we select another node at random.
        first_parent_index = second_parent_index = 0
        while first_parent_index == second_parent_index:
            first_parent_index = random.randint(0, num_choices-1)
            second_parent_index = random.randint(0, num_choices-1)
        return [choices[first_parent_index], choices[second_parent_index]]

    def reachableByAllFrontiers(self, node):
        """        
        Arguments:
            node {Node} -- Node in question.

        Returns:
            bool -- True if node is reachable by all frontier nodes
        """

        for front in list(self.frontier_nodes):
            if node not in front.reachable:
                return False
        return True

    def needsReissue(self, node):
        """
        Arguments:
            node {Node} -- Node in question.

        Returns:
            bool -- True if both of node's parents are reachableByAll (means node is too deep to be not accepted/reachableByAll itself and needs reissue), False otherwise.
        """

        for pointer in node.tx.pointers:
            if not self.reachableByAllFrontiers(self.chain_pointers[pointer]):
                return False
        return True

    # ==Overwritten methods============

    def makeTx(self):
        """Makes a new transaction, connects it to the chain, and returns it.

        Returns:
            Tx -- Newly created transaction.
        """

        new_tx = transaction.Tx(self.simulation.tick, self.id, self.id_bag.getNextId())
        parents = self.getNewParents()
        assert parents  # Should always have at least one (genesis tx).
        for parent in parents:
            parent_hash = parent.hash()
            assert parent_hash in self.chain_pointers
            new_tx.pointers.append(parent_hash)
        self.sheep_tx.add(new_tx)
        self.simulation.all_tx.append(new_tx)
        return new_tx

    def checkAllTx(self):
        """Check all nodes for consensus (runs an implicit "tau function" on each node, but all at once because it's faster), and whether sheep need to be reissued.
        """

        self.reissue_ids = set()  # Only reset when you checkAll so that it stays full!
        for node in self.chain_pointers.values():
            if self.reachableByAllFrontiers(node):
                if node.tx not in self.consensed_tx:
                    node.tx.addEvent(self.simulation.tick, self.id, transaction.State.CONSENSUS)
                    self.consensed_tx.add(node.tx)
                if node.tx.id in self.reissue_ids:
                    self.reissue_ids.remove(node.tx.id)
            else:
                if node.tx in self.consensed_tx:
                    node.tx.addEvent(self.simulation.tick, self.id, transaction.State.DISCONSENSED)
                    self.consensed_tx.remove(node.tx)
                if node.tx in self.sheep_tx and self.needsReissue(node):
                    self.reissue_ids.add(node.tx.id)
