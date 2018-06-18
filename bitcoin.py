import random
import networkx as nx
import matplotlib.pyplot as plt
import tx
import miner
import plot

class Node:
    """node in the bitcoin miner's personal view of the blockchain"""

    def __init__(self, t):
        self.tx = t
        self.children = []
        self.depth = 0
        self.reachable = set()  # used by Iota, not Bitcoin


class Bitcoin(miner.Miner):
    name = "Bitcoin"

    def __init__(self, i, gen, g, o):
        miner.Miner.__init__(self, i, gen, g, o)  # calls self.start()
        self.root = Node(gen)
        self.chain = {}  # maps has to nodes whose tx has that hash
        self.chain[gen.hash()] = self.root
        self.front = set([self.root])  # update this as nodes are added instead of recomputing!
        self.accepted = set()  # set of tx I've accepted (only used to avoid spamming tx.history events); don't count on this for reporting, use tx.history instead
        self.root.tx.addEvent(-1, self.id, tx.State.CONSENSUS)
        self.accepted.add(self.root.tx)
        self.sheep = set()  # queue of tx to shepherd
        self.reissue = set()  # temporary set of ids that need to be reissued (populated anew each time checkAll is called)
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

    def addToChain(self, tAdd, sender):
        newn = Node(tAdd)
        temp = [newn] + self.orphans[:]
        self.orphans = []
        first = True
        changed = True
        broadcast = []
        while changed and temp: # keep checking all nodes until nothing changed (or there are no orphans)
            changed = False
            for n in temp:
                t = n.tx
                parents = [(self.findInChain(p), p) for p in t.pointers] # works for both bitcoin and iota
                if None not in [p[0] for p in parents]:
                    assert t.hash() not in self.chain  # make sure I've never seen this tx before
                    t.addEvent(self.over.tick, self.id, tx.State.PRE)
                    self.chain[t.hash()] = n
                    broadcast.append(t)
                    for parent, pointer in parents:
                        assert n not in parent.children
                        parent.children.append(n)
                        newDepth = parent.depth + 1
                        if newDepth > n.depth:
                            n.depth = newDepth
                        n.reachable |= set([parent]) | parent.reachable # only needed in iota
                        if parent in self.front:
                            self.front.remove(parent)
                    self.front.add(n)
                    changed = True
                    temp.remove(n)#remove from temp as we go, copy to self.orphans at the end
                elif first:  # only for new orphan
                    assert sender != self.id  # I'm processing a node I just created but I should never have created an orphan
                    for parent, pointer in parents:
                        if parent is None:
                            self.sendRequest(sender, pointer)
            first = False
        self.orphans = temp
        return broadcast

    def checkRec(self, node, maxDepth=-99, d=0):
        """returns maxDepth
        if maxDepth is > 0, will mark tx as accepted if they are in the deepest chain and at least 6 deep (will also add sheep to self.reissue if appropriate)
        """
        if not node.children:
            # the only portion of the the checks at the end of this function that need to be run on leaf nodes
            if maxDepth > 0 and node.tx in self.sheep and d < maxDepth - self.over.bitcoinAcceptDepth:
                self.reissue.add(node.tx.id)
            return d

        mx = 0
        for c in node.children:
            i = self.checkRec(c, maxDepth, d+1)
            if i > mx:
                mx = i

        if maxDepth > 0:
            if mx == maxDepth and mx - d >= self.over.bitcoinAcceptDepth:
                if node.tx not in self.accepted:
                    node.tx.addEvent(self.over.tick, self.id, tx.State.CONSENSUS)
                    self.accepted.add(node.tx)
                if node.tx.id in self.reissue:
                    self.reissue.remove(node.tx.id)  # accepted, so it doesn't need to be reiussed (this will happen because reissued tx are still saved in old forks)
            elif mx != maxDepth:
                if node.tx in self.accepted:
                    node.tx.addEvent(self.over.tick, self.id, tx.State.DISCONSENSED)
                    self.accepted.remove(node.tx)
                # below:first condition says that it's a sheep on an unaccepted fork, second condition says whether it's time to rebroadcast (max depth of fork is 6+ deep)
                if node.tx in self.sheep and mx < maxDepth - self.over.bitcoinAcceptDepth:
                    self.reissue.add(node.tx.id)  # the order these will be added to reissue is leaf-up
        return mx

    # ==overwritten methods============

    def makeTx(self):
        """return tx
        make sure to append to self.over.allTx
        """
        newtx = tx.Tx(self.over.tick, self.id, self.over.idBag.getNextId())
        sortedFronts = sorted(self.front, reverse=True,key=lambda n: n.depth)
        choices = [n for n in sortedFronts if n.depth == sortedFronts[0].depth] # only consider the deepest front nodes
        parent = random.choice(choices)
        newtx.pointers.append(parent.tx.hash())
        self.sheep.add(newtx)
        self.over.allTx.append(newtx)
        return newtx

    # How BITCOIN miners handle shepherding
    # checkall, which should also mark nodes as need-to-reissue
    # give "need-to-reissue" to sim.py to setup IdBag

    def checkReissues(self):
        """a chance for the miner to put its need-to-reissue tx in o.IdBag"""
        for i in self.reissue:
            self.over.idBag.addId(i, self)

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
        if maxDepth < self.over.bitcoinAcceptDepth:
            return
        self.checkRec(self.root, maxDepth)

    def removeSheep(self, i):
        """overseer will call this to tell the miner that it doesn't have to shepherd an id anymore"""
        x = None
        for s in self.sheep:
            if s.id == i:
                x = s
                break
        if x:
            self.sheep.remove(x)
        if i in self.reissue:
            self.reissue.remove(i)
