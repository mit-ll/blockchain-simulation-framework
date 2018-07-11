from enum import Enum
import logging
import random
import transaction


class Message:
    """Message from one miner to another.
    """

    def __init__(self, sender_id, msg_type, content):
        """
        Arguments:
            sender_id {int} -- Id of sending miner.
            msg_type {Type} -- Type of message.
            content {Tx|str} -- Tx if type is BLOCK, hash string if type is REQUEST.
        """

        self.sender = sender_id
        self.type = msg_type
        self.content = content


class Type(Enum):
    """Enumeration of message types.
    """

    BLOCK = 0
    REQUEST = 1


class Miner:
    """Miner superclass (also implements naive miner).
    """

    name = "Naive"

    def __init__(self, miner_id, genesis_tx, graph, simulation, power=1):
        """        
        Arguments:
            miner_id {int} -- Miner's id.
            genesis_tx {Tx} -- Blockchain protocol's genesis transaction.
            graph {networkx.Graph} -- Graph of network being simulated.
            simulation {Simulation} -- Simulation object that stores settings and simulation variables.
            power {int} -- Miner's power relative to other miners.
        """
        self.id = miner_id
        self.power = power
        self.graph = graph
        self.simulation = simulation
        self.pre_queue = []
        self.queue = []
        self.seen_tx = {}  # Dictionary mapping hash to tx for seen tx.
        self.seen_tx[genesis_tx.hash] = genesis_tx
        self.changed_last_step = False
        self.id_bag = simulation.protocol.getIdBag(simulation)
        self.adjacencies = {}  # These will be filled in by simulation.finalizeMiners().

    def pushMsg(self, msg, delay=0):
        """Push message into prequeue. Will be added to queue when flushMsgs() is called.
        This is done to prevent miners that execute later in a step from acting on msgs from miners that executed earlier that step.

        Arguments:
            msg {Message} -- Message to push onto queue.

        Keyword Arguments:
            delay {int} -- Delay in ticks until message arrives. (default: {0})
        """
        self.pre_queue.append([msg, delay])

    def flushMsgs(self):
        """Adds all messages from prequeue to queue.
        """

        self.queue = self.pre_queue[:]
        self.pre_queue = []

    def popMsg(self):
        """Pops all messages with delay 0 from queue, decrements delay of all other messages in queue.

        Returns:
            list(Message) -- List of all messages recieved this tick.
        """

        if not self.queue:
            return []
        returned_msgs = []
        for msg, delay in self.queue:
            delay -= 1
            if delay < 1:
                returned_msgs.append(msg)
            else:
                self.pushMsg(msg, delay)
        self.queue = []
        return returned_msgs

    def broadcast(self, tx):
        """Broadcast tx to all adjacent miners.

        Arguments:
            tx {Tx} -- Transaction to broadcast.
        """

        for neighbor_id in self.adjacencies:
            self.sendMsg(neighbor_id, Message(self.id, Type.BLOCK, tx))

    def sendMsg(self, recipient_id, msg):
        """Send message to a recipient miner.

        Arguments:
            recipient_id {int} -- Recipient miner's id.
            msg {Message} -- Message to send.
        """

        assert not (msg.type == Type.BLOCK and set(msg.content.pointers) - set(self.seen_tx))  # Shouldn't send a tx if I don't know tx for all of its pointers.
        neighbor, delay = self.adjacencies[recipient_id]
        neighbor.pushMsg(msg, delay.sample())

    def sendRequest(self, recipient_id, target_hash):
        """Send request for a tx with target_hash.
        Provided so subclasses don't have to know about Message/Type classes.

        Arguments:
            recipient_id {int} -- Recipient miner's id.
            target_hash {str} -- Hash of transaction being requested.
        """

        self.sendMsg(recipient_id, Message(self.id, Type.REQUEST, target_hash))

    def handleNewTx(self, tx, sender_id):
        """Process new tx by adding it to miner's view of blockain and broadcasting tx if appropriate.

        Arguments:
            tx {Tx} -- Transaction to handle.
            sender_id {int} -- Id of miner who we received this tx from.
        """

        self.seen_tx[tx.hash] = tx
        for x in self.processNewTx(tx, sender_id):  # ABSTRACT - Process tx.
            self.broadcast(x)  # Broadcast new or first-time-seen-NON-ORPHAN tx only.

    def handleMsgs(self):
        """Receive all messages and handle by adding new tx to chain and sending requested tx.
        """

        force_sheep_check = self.changed_last_step
        self.changed_last_step = False
        if not self.queue:
            return
        
        need_to_check = False
        for msg in self.popMsg():  # Receive message(s) from queue.
            if msg.type == Type.BLOCK:
                new_tx = msg.content
                if new_tx.hash in self.seen_tx:
                    continue
                need_to_check = True
                self.changed_last_step = True
                self.handleNewTx(new_tx, msg.sender)
            elif msg.type == Type.REQUEST:  # Requests are issued by other miners.
                target_hash = msg.content
                assert target_hash in self.seen_tx  # I should never get a request for a tx I haven't seen.
                requestedTx = self.seen_tx[target_hash]
                self.sendMsg(msg.sender, Message(self.id, Type.BLOCK, requestedTx))
        if need_to_check or (self.hasSheep() and force_sheep_check):  # Have to check every time if has sheep.
            self.checkAllTx()

    def makeNewTx(self):
        """Make a new transaction (simulation rolled protocol's generation probability).
        """
        new_tx = self.makeTx()  # ABSTRACT - Make a new tx.
        logging.info("New tx (%d) created by miner %d" % (new_tx.id, self.id))
        self.changed_last_step = True
        self.handleNewTx(new_tx, self.id)
        self.checkAllTx()

    # ==ABSTRACT====================================
    # Copy and overwrite these method in subclasses.

    def makeTx(self):
        """Makes a new transaction, connects it to the chain, and returns it.

        Returns:
            Tx -- Newly created transaction.
        """
        new_tx = transaction.Tx(self.simulation.tick, self.id, self.id_bag.getNextId(), [])
        self.simulation.all_tx.append(new_tx)
        return new_tx

    def checkReissues(self):
        """Miner adds any ids that need to be reiussed to its idBag.
        """
        return None

    def hasSheep(self):
        """        
        Returns:
            bool -- True if the miner has sheep, False otherwise.
        """
        return False

    def processNewTx(self, new_tx, sender_id):
        """Add new_tx to the miner's view of the blockchain.

        Arguments:
            new_tx {Tx} -- New transaction to add.
            sender_id {int} -- Id of the node that sent us new_tx.

        Returns:
            list(Tx) -- List of transactions to broadcast to neighbors.
        """
        new_tx.addEvent(self.simulation.tick, self.id, transaction.State.CONSENSUS)
        return [new_tx]

    def checkAllTx(self):
        """Check all nodes for consensus (runs an implicit "tau function" on each node, but all at once because it's faster), and whether sheep need to be reissued.
        """
        return None

    def removeSheep(self, sheep_id):
        """Overseer will call this to tell the miner that it doesn't have to shepherd an id anymore.

        Arguments:
            sheep_id {int} -- Id of tx to remove from sheep_tx.
        """
        return None
