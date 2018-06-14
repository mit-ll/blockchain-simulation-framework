import random
import tx


class Message:
    def __init__(self, s, t, c):
        self.sender = s
        self.type = t
        self.content = c


class Type:
    BLOCK = 0
    REQUEST = 1


class Miner:
    name = "Naive"

    def __init__(self, i, gen, g, o):
        self.id = i
        self.g = g
        self.o = o
        self.preq = []  # to prevent miners that execute later in a step from acting on msgs from miners that executed earlier that step
        self.queue = []
        self.seen = {}  # dictionary mapping hash to tx for seen tx
        self.seen[gen.hash()] = gen
        self.hadChangeLastStep = False

    def pushMsg(self, msg, delay=0):
        self.preq.append([msg, delay])

    def flushMsgs(self):
        self.queue = self.preq[:]
        self.preq = []

    def popMsg(self):
        qcopy = self.queue[:]
        self.queue = []
        ret = []
        for msg, d in qcopy:
            d -= 1
            if d < 1:
                ret.append(msg)
            else:
                self.pushMsg(msg, d)
        return ret  # should a miner only receive 1 message at a time, or can it do all at once like this?

    def broadcast(self, adj, t):
        """broadcast tx to all adjacent miners"""
        for i in adj:
            self.sendMsg(i, Message(self.id, Type.BLOCK, t))

    def sendMsg(self, recipient, msg):
        assert not (msg.type == Type.BLOCK and set(msg.content.pointers) - set(self.seen)) #shouldn't send a tx if I don't know tx for all of its pointers
        self.g.nodes[recipient]['miner'].pushMsg(msg, self.o.getDelay())

    def sendRequest(self, recipient, targetHash):  # so subclasses don't have to know about Message/Type classes
        self.sendMsg(recipient, Message(self.id, Type.REQUEST, targetHash))

    def handleTx(self, t, sender, adj):
        self.seen[t.hash()] = t
        for x in self.process(t, sender):  # ABSTRACT - process tx
            self.broadcast(adj, x)  # broadcast new/first-time-seen-NOT-ORPHAN tx only

    def step(self, adj):
        """adj is adjacent miners"""
        forceSheepCheck = self.hadChangeLastStep
        self.hadChangeLastStep = False
        needToCheck = False
        for msg in self.popMsg():  # receive message(s) from queue
            if msg.type == Type.BLOCK:
                t = msg.content
                if t.hash() in self.seen:
                    continue
                needToCheck = True
                self.hadChangeLastStep = True
                self.handleTx(t, msg.sender, adj)
            elif msg.type == Type.REQUEST:  # requests are issued by other miners
                targetHash = msg.content
                assert targetHash in self.seen # I should never get a request for a tx I haven't seen
                requestedTx = self.seen[targetHash]
                self.sendMsg(msg.sender, Message(self.id, Type.BLOCK, requestedTx))
        if needToCheck or (self.hasSheep() and forceSheepCheck):  # have to check every time if has sheep...
            self.checkAll()

    def postStep(self, adj):
        if random.random() < self.o.txGenProb:  # chance to gen tx (important that this happens AFTER processing messages)
            newtx = self.makeTx()  # ABSTRACT - make a new tx
            self.hadChangeLastStep = True
            self.handleTx(newtx, self.id, adj)
            self.checkAll()

    # ==ABSTRACT====================================
    # copy and overwrite these method in subclasses!

    def makeTx(self):
        """return tx
        make sure to append to self.o.allTx
        """
        newtx = tx.Tx(self.o.tick, self.id, self.o.idBag.getNextId())
        self.o.allTx.append(newtx)
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
        t.addEvent(self.o.tick, self.id, tx.State.CONSENSUS)
        return [t]

    def checkAll(self):
        """check all nodes for consensus (calling Tau)"""
        return None

    def removeSheep(self, i):
        """overseer will call this to tell the miner that it doesn't have to shepherd an id anymore"""
        return None
