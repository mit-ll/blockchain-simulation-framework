import random
import tx


class Message:
    def __init__(self, s, t, c):
        self.sender = s
        self.type = t
        self.content = c  # tx if type is BLOCK, hash string if type is REQUEST.


class Type:
    BLOCK = 0
    REQUEST = 1


class Miner:
    name = "Naive"

    def __init__(self, id, genesis_tx, graph, simulation):
        self.id = id
        self.graph = graph
        self.simulation = simulation
        self.preq = []  # To prevent miners that execute later in a step from acting on msgs from miners that executed earlier that step.
        self.queue = []
        self.seen = {}  # Dictionary mapping hash to tx for seen tx.
        self.seen[genesis_tx.hash()] = genesis_tx
        self.hadChangeLastStep = False
        self.id_bag = simulation.protocol.getIdBag(simulation)
        self.adjacencies = None  # Will be filled in by simulation.updateMinerAdjacencies().

    def pushMsg(self, msg, delay=0):
        self.preq.append([msg, delay])

    def flushMsgs(self):
        self.queue = self.preq[:]
        self.preq = []

    def popMsg(self):
        qcopy = self.queue[:]
        self.queue = []
        msgs = []
        for msg, d in qcopy:
            d -= 1
            if d < 1:
                msgs.append(msg)
            else:
                self.pushMsg(msg, d)
        return msgs  # should a miner only receive 1 message at a time, or can it do all at once like this?

    def broadcast(self, t):
        """broadcast tx to all adjacent miners"""
        for i in self.adjacencies:
            self.sendMsg(i, Message(self.id, Type.BLOCK, t))

    def sendMsg(self, recipient, msg):
        assert not (msg.type == Type.BLOCK and set(msg.content.pointers) - set(self.seen))  # Shouldn't send a tx if I don't know tx for all of its pointers.
        edge = self.adjacencies[recipient]
        self.graph.nodes[recipient]['miner'].pushMsg(msg, edge['network_delay'].sample())

    def sendRequest(self, recipient, targetHash):  # So subclasses don't have to know about Message/Type classes.
        self.sendMsg(recipient, Message(self.id, Type.REQUEST, targetHash))

    def handleTx(self, t, sender):
        self.seen[t.hash()] = t
        for x in self.process(t, sender):  # ABSTRACT - Process tx.
            self.broadcast(x)  # broadcast new/first-time-seen-NOT-ORPHAN tx only

    def step(self):
        forceSheepCheck = self.hadChangeLastStep
        self.hadChangeLastStep = False
        needToCheck = False
        for msg in self.popMsg():  # Receive message(s) from queue.
            if msg.type == Type.BLOCK:
                t = msg.content
                if t.hash() in self.seen:
                    continue
                needToCheck = True
                self.hadChangeLastStep = True
                self.handleTx(t, msg.sender)
            elif msg.type == Type.REQUEST:  # Requests are issued by other miners.
                targetHash = msg.content
                assert targetHash in self.seen  # I should never get a request for a tx I haven't seen.
                requestedTx = self.seen[targetHash]
                self.sendMsg(msg.sender, Message(self.id, Type.BLOCK, requestedTx))
        if needToCheck or (self.hasSheep() and forceSheepCheck):  # Have to check every time if has sheep.
            self.checkAll()

    def postStep(self):
        if random.random() < self.simulation.protocol.transaction_generation_probability:  # Chance to generate a new tx (important that this happens AFTER processing messages).
            newtx = self.makeTx()  # ABSTRACT - Make a new tx.
            self.hadChangeLastStep = True
            self.handleTx(newtx, self.id)
            self.checkAll()

    # ==ABSTRACT====================================
    # Copy and overwrite these method in subclasses.

    def makeTx(self):
        """return tx
        make sure to append to self.over.allTx
        """
        newtx = tx.Tx(self.simulation.tick, self.id, self.id_bag.getNextId())
        self.simulation.all_tx.append(newtx)
        return newtx

    def checkReissues(self):
        """a chance for the miner to put its need-to-reissue tx in o.IdBag"""
        return None

    def hasSheep(self):
        """returns whether miner has sheep"""
        return False

    def process(self, t, sender):
        """update view
        return list of tx to broadcast
        """
        t.addEvent(self.simulation.tick, self.id, tx.State.CONSENSUS)
        return [t]

    def checkAll(self):
        """check all nodes for consensus (calling Tau)"""
        return None

    def removeSheep(self, i):
        """overseer will call this to tell the miner that it doesn't have to shepherd an id anymore"""
        return None
