import random
import networkx as nx
import matplotlib.pyplot as plt
import transaction
import miner
import plot


class Node:
    """Node in the Bitcoin miner's personal view of the blockchain. Provides forward pointers through blockchain for convenience.
    """

    def __init__(self, tx):
        """
        Arguments:
            tx {Tx} -- The transaction that the node represents.
        """

        self.tx = tx
        self.children = []
        self.depth = 0  # Used by Bitcoin, not Iota.
        self.reachable = set()  # Used by Iota, not Bitcoin.


class Bitcoin(miner.Miner):
    """Bitcoin protocol miner.
    """

    name = "Bitcoin"

    def __init__(self, miner_id, genesis_tx, graph, simulation, power=1):
        """        
        Arguments:
            miner_id {int} -- Miner's id.
            genesis_tx {Tx} -- Blockchain protocol's genesis transaction.
            graph {networkx.Graph} -- Graph of network being simulated.
            simulation {Simulation} -- Simulation object that stores settings and simulation variables.
            power {int} -- Miner's power relative to other miners.
        """

        miner.Miner.__init__(self, miner_id, genesis_tx, graph, simulation, power)
        self.root = Node(genesis_tx)
        self.chain_pointers = {}  # Maps hash to node whose tx has that hash.
        self.chain_pointers[genesis_tx.hash] = self.root
        self.frontier_nodes = set([self.root])  # Update this as nodes are added instead of recomputing deepest nodes.
        self.consensed_tx = set()  # Set of tx I've accepted (only used to avoid spamming tx.history events); don't count on this for reporting, use tx.history instead.
        self.root.tx.addEvent(-1, self.id, transaction.State.CONSENSUS)
        self.consensed_tx.add(self.root.tx)
        self.sheep_tx = set()  # Queue of tx to shepherd.
        self.reissue_ids = set()  # Temporary set of ids that need to be reissued (populated anew each time checkAll is called).
        self.orphan_nodes = []

        self.file_num = 0

    def findInChain(self, target_hash):
        """
        Arguments:
            target_hash {str} -- Hash of the tx we're looking for.

        Returns:
            {Node|None} -- Returns the node from chain whose tx has the target hash, or None if no such tx is in chain.
        """

        if target_hash in self.chain_pointers:
            return self.chain_pointers[target_hash]
        return None

    def addToChain(self, tx_to_add, sender_id):
        """Adds tx_to_add to the chain if all of its parents are in the chain, otherwise it becomes an orphan.
        Loops through all orphans and tries to connect them, leaving unconnectable nodes as orphans.

        Arguments:
            tx_to_add {Tx} -- Tx to be added to the chain.
            sender_id {int} -- Id of the node that sent tx_to_add; used to send a request if we haven't seen any/all of its parents.

        Returns:
            list(Tx) -- List of tx that were just added to the chain to broadcast to neighbors.
        """

        new_node = Node(tx_to_add)
        nodes_to_add = [new_node] + self.orphan_nodes[:]
        self.orphan_nodes = []
        first = True
        to_broadcast = []
        while nodes_to_add:  # Keep checking all nodes until nothing changed (or there are no orphans).
            chain_changed = False
            index = 0  # Need to use index because we will be removing items as we iterate through nodes_to_add.
            while index < len(nodes_to_add):
                node_to_add = nodes_to_add[index]
                tx_to_add = node_to_add.tx
                parents = [(self.findInChain(parent), parent) for parent in tx_to_add.pointers]  # Find node associated with each parent (works for both bitcoin and iota).
                if None not in [p[0] for p in parents]:
                    assert tx_to_add.hash not in self.chain_pointers  # Make sure I've never seen this tx before.
                    tx_to_add.addEvent(self.simulation.tick, self.id, transaction.State.PRE_CONSENSUS)
                    self.chain_pointers[tx_to_add.hash] = node_to_add
                    to_broadcast.append(tx_to_add)
                    for parent, pointer in parents:
                        assert node_to_add not in parent.children
                        parent.children.append(node_to_add)
                        new_depth = parent.depth + 1
                        if new_depth > node_to_add.depth:
                            node_to_add.depth = new_depth
                        node_to_add.reachable |= set([parent]) | parent.reachable  # Only needed in Iota.
                        if parent in self.frontier_nodes:
                            self.frontier_nodes.remove(parent)
                    self.frontier_nodes.add(node_to_add)
                    chain_changed = True
                    nodes_to_add.remove(node_to_add)  # Remove from nodes_to_add as we go, copy to self.orphan_nodes at the end.
                    index -= 1

                    # Graph generation.
                    if False and self.id == 0:
                        fname = './graphs/chainout%d.gv' % self.file_num
                        plot.plotDag(self, fname, False)
                        self.file_num += 1

                elif first:  # Only for new orphan.
                    assert sender_id != self.id  # I'm processing a node I just created but I should never have created an orphan.
                    for parent, pointer in parents:
                        if parent is None:
                            self.sendRequest(sender_id, pointer)
                index += 1
                first = False
            if not chain_changed:
                break
        self.orphan_nodes = nodes_to_add  # Leftover nodes are orphans.
        return to_broadcast

    def checkTxRecursion(self, node, max_depth=-99, curr_depth=0):
        """Recursive function with dual functionality:
        Always returns maximum depth of the chain.
        If maxDepth is > 0, will also mark tx as accepted if they are in the deepest chain and at least as deep as the accept depth (will also add sheep to self.reissue_ids if appropriate).

        Arguments:
            node {Node} -- The current node being examined by the recursive function.

        Keyword Arguments:
            max_depth {int} -- The maximum depth of the chain. (default: {-99})
            curr_depth {int} -- The current node's depth (post-recursive-call). (default: {0})

        Returns:
            int -- Maximum depth of the chain.
        """

        if not node.children:
            # The only portion of the the checks at the end of this function that need to be run on leaf nodes.
            if max_depth > 0 and node.tx in self.sheep_tx and curr_depth < max_depth - self.simulation.protocol.accept_depth:
                self.reissue_ids.add(node.tx.id)
            return curr_depth

        local_max = 0
        for child in node.children:
            child_max = self.checkTxRecursion(child, max_depth, curr_depth+1)
            if child_max > local_max:
                local_max = child_max

        if max_depth > 0:
            if local_max == max_depth and local_max - curr_depth >= self.simulation.protocol.accept_depth:
                if node.tx not in self.consensed_tx:
                    node.tx.addEvent(self.simulation.tick, self.id, transaction.State.CONSENSUS)
                    self.consensed_tx.add(node.tx)
                if node.tx.id in self.reissue_ids:
                    self.reissue_ids.remove(node.tx.id)  # Consensed, so it doesn't need to be reiussed (this will happen because reissued tx are still saved in old forks).
            elif local_max != max_depth:
                if node.tx in self.consensed_tx:
                    node.tx.addEvent(self.simulation.tick, self.id, transaction.State.DISCONSENSED)
                    self.consensed_tx.remove(node.tx)
                # Below: first condition says that it's a sheep on an unaccepted fork, second condition says whether it's time to rebroadcast (max depth of fork is 6+ deep).
                if node.tx in self.sheep_tx and local_max < max_depth - self.simulation.protocol.accept_depth:
                    self.reissue_ids.add(node.tx.id)  # The order these will be added to reissue is leaf-up.
        return local_max

    # ==Overwritten methods============

    def makeTx(self):
        """Makes a new transaction, connects it to the chain, and returns it.

        Returns:
            Tx -- Newly created transaction.
        """

        sorted_fronts = sorted(self.frontier_nodes, reverse=True, key=lambda n: n.depth)
        parent_choices = [n for n in sorted_fronts if n.depth == sorted_fronts[0].depth]  # Only consider the deepest frontier nodes.
        parent = random.choice(parent_choices)
        new_tx = transaction.Tx(self.simulation.tick, self.id, self.id_bag.getNextId(), [parent.tx.hash])
        self.sheep_tx.add(new_tx)
        self.simulation.all_tx.append(new_tx)
        return new_tx

    def checkReissues(self):
        """Miner adds any ids that need to be reiussed to its idBag.
        """

        for i in self.reissue_ids:
            self.id_bag.addId(i, self)

    def hasSheep(self):
        """        
        Returns:
            bool -- True if the miner has sheep, False otherwise.
        """

        if self.sheep_tx:
            return True
        return False

    def processNewTx(self, new_tx, sender_id):
        """Add new_tx to the miner's view of the blockchain.

        Arguments:
            new_tx {Tx} -- New transaction to add.
            sender_id {int} -- Id of the node that sent us new_tx.

        Returns:
            list(Tx) -- List of transactions to broadcast to neighbors.
        """

        return self.addToChain(new_tx, sender_id)

    def checkAllTx(self):
        """Check all nodes for consensus (runs an implicit "tau function" on each node, but all at once because it's faster), and whether sheep need to be reissued.
        """

        self.reissue_ids = set()  # Only reset when you checkAll so that it stays full.
        max_depth = self.checkTxRecursion(self.root)
        if max_depth < self.simulation.protocol.accept_depth:
            return
        self.checkTxRecursion(self.root, max_depth)

    def removeSheep(self, sheep_id):
        """Overseer will call this to tell the miner that it doesn't have to shepherd an id anymore.

        Arguments:
            sheep_id {int} -- Id of tx to remove from sheep_tx.
        """

        target_sheep = None
        for sheep in self.sheep_tx:
            if sheep.id == sheep_id:
                target_sheep = sheep
                break
        if target_sheep:
            self.sheep_tx.remove(target_sheep)
        if sheep_id in self.reissue_ids:
            self.reissue_ids.remove(sheep_id)
