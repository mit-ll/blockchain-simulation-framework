import random
import networkx as nx
import matplotlib.pyplot as plt
import tx
import miner
import plot


def deepestChildren(node):
    return deepRec(node)[0]


def deepRec(node, d=0):
    if not node.children:
        return [node], d
    l = []
    mx = 0
    for c in node.children:
        subl, subd = deepRec(c, d+1)
        if subd > mx:
            l = []
            mx = subd
        if subd == mx:
            l += subl
    return l, mx


class Node:
    """node in the bitcoin miner's personal view of the blockchain"""

    def __init__(self, t):
        self.tx = t
        self.children = []


class Bitcoin(miner.Miner):
    name = "Bitcoin"

    def __init__(self, i, gen, g, o):
        miner.Miner.__init__(self, i, gen, g, o)  # calls self.start()
        self.root = Node(gen)
        self.chain = {}  # maps has to nodes whose tx has that hash
        self.chain[gen.hash()] = self.root
        self.accepted = set()  # set of tx I've accepted (only used to avoid spamming tx.history events); don't count on this for reporting, use tx.history instead
        self.root.tx.addEvent(-1, self.id, tx.State.CONSENSUS)
        self.accepted.add(self.root.tx)
        self.sheep = set()  # queue of tx to shepherd
        self.reissue = set()  # temporary set of ids that need to be reissued (populated by checkAll; should be reset every tick)
        self.orphans = []

    def findInChain(self, target):
        """returns the tx from self.chain with the target hash"""
        if target in self.chain:
            return self.chain[target]
        return None

    def childOfOrphan(self, t):
        """returns False if earliest parent is genesis tx (t is "rooted in genesis tx")
        returns True otherwise (t is an orphan or child of an orphan)
        """
        if not t.pointers:  # only genesis tx has not pointers
            return False
        parent = self.findInChain(t.pointers[0])
        if parent is None:
            return True
        else:
            return self.childOfOrphan(parent.tx)

    #
    def addToChain(self, tAdd, sender):
        """
        t is a tx (with pointer already set), and miner.py has already checked that we haven't seen it
        returns list of tx to broadcast to neighbors
        from bitcoin wiki (https://en.bitcoin.it/wiki/Protocol_rules):
                add this to orphan blocks, then query peer we got this from for 1st missing orphan block in prev chain; done with block
                (also, when handling orphan blocks:) For each orphan block for which this block is its prev, run all these steps (including this one) recursively on that orphan
        keep list of orphan nodes, still put them in self.chain so we have pointers to them, and whenever we get a new node, check orphans to see if it fits!
        """
        newn = Node(tAdd)
        self.chain[tAdd.hash()] = newn
        temp = [newn] + self.orphans[:]
        self.orphans = []
        first = True  # this matters for non-orphan-broadcast and for not requesting old orphans from current "sender" who has nothing to do with them
        for n in temp:  # for new node ("first" is True) and all orphans ("first" is False)
            t = n.tx
            parent = self.findInChain(t.pointers[0])  # only ever one pointer in Bitcoin
            if first:
                broadcast = not self.childOfOrphan(t)  # do not broadcast if oldest parent is orphan (includes orphan AND children of orphans!!)
                t.addEvent(self.o.tick, self.id, tx.State.PRE)  # putting this here means that orphans are marked PRE before they join the genesis-rooted tree
            if parent is None:
                self.orphans.append(n)
                if first:  # only for new orphan
                    assert sender != self.id  # I'm processing a node I just created but I should never have created an orphan
                    self.sendRequest(sender, t.pointers[0])
            else:
                parent.children.append(n)
        # (Being a sheep and being an orphan are mutually exclusive; new nodes are added to originator's view, rooted at the genesis block)
            first = False
        if broadcast:
            return [tAdd]
        else:
            return []

    def checkRec(self, node, maxDepth=-99, d=0):
        """returns maxDepth
        if maxDepth is > 0, will mark tx as accepted if they are in the deepest chain and at least 6 deep (will also add sheep to self.reissue if appropriate)
        """
        if not node.children:
            # the only portion of the the checks at the end of this function that need to be run on leaf nodes
            if maxDepth > 0 and node.tx in self.sheep and d < maxDepth - self.o.bitcoinAcceptDepth:
                self.reissue.add(node.tx.id)
            return d

        mx = 0
        for c in node.children:
            i = self.checkRec(c, maxDepth, d+1)
            if i > mx:
                mx = i

        if maxDepth > 0:
            if mx == maxDepth and mx - d >= self.o.bitcoinAcceptDepth:
                if node.tx not in self.accepted:
                    node.tx.addEvent(self.o.tick, self.id, tx.State.CONSENSUS)
                    self.accepted.add(node.tx)
                if node.tx.id in self.reissue:
                    self.reissue.remove(node.tx.id)  # accepted, so it doesn't need to be reiussed (this will happen because reissued tx are still saved in old forks)
            elif mx != maxDepth:
                if node.tx in self.accepted:
                    node.tx.addEvent(self.o.tick, self.id, tx.State.DISCONSENSED)
                    self.accepted.remove(node.tx)
                # below:first condition says that it's a sheep on an unaccepted fork, second condition says whether it's time to rebroadcast (max depth of fork is 6+ deep)
                if node.tx in self.sheep and mx < maxDepth - self.o.bitcoinAcceptDepth:
                    self.reissue.add(node.tx.id)  # the order these will be added to reissue is leaf-up
        return mx

    # ==overwritten methods============

    def makeTx(self):
        """return tx
        make sure to append to self.o.allTx
        """
        newtx = tx.Tx(self.o.tick, self.id, self.o.idBag.getNextId())
        deepest = deepestChildren(self.root)
        parent = random.choice(deepest)
        newtx.pointers.append(parent.tx.hash())
        self.sheep.add(newtx)
        self.o.allTx.append(newtx)
        return newtx

    # How BITCOIN miners handle shepherding
    # checkall, which should also mark nodes as need-to-reissue
    # give "need-to-reissue" to sim.py to setup IdBag

    def checkReissues(self):
        """a chance for the miner to put its need-to-reissue tx in o.IdBag"""
        for i in self.reissue:
            self.o.idBag.addId(i, self)

    def hasSheep(self):
        """returns whether miner has sheep"""
        if self.sheep:
            return True
        return False

    def process(self, t, sender):
        """update view
        return list of tx to broadcast
        """
        return self.addToChain(t, sender)

    def checkAll(self):
        """check all nodes for consensus (runs an implicit "tau" on each node, but all at once because it's faster)"""
        self.reissue = set()  # only reset when you checkAll so that it stays full
        maxDepth = self.checkRec(self.root)
        if maxDepth < self.o.bitcoinAcceptDepth:
            return
        self.checkRec(self.root, maxDepth)

    def removeSheep(self, i):
        """overseer will call this to tell the miner that it doesn't have to shepherd an id anymore"""
        x = None
        for s in self.sheep:
            if s.id == i:
                x = s
        if x:
            self.sheep.remove(x)
        if i in self.reissue:
            self.reissue.remove(i)
