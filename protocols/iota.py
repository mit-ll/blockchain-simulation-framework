import random
import networkx as nx
import tx
import miner
import bitcoin


class Iota(bitcoin.Bitcoin):
    name = "Iota"

    def __init__(self, i, gen, g, o):
        bitcoin.Bitcoin.__init__(self, i, gen, g, o)

    def getNewParents(self):
        """returns list of 1 or 2 parent tx for new tx"""
        choices = list(self.front)
        if self.root in choices and len(choices) >= 3:
            choices.remove(self.root)
        choices = [c.tx for c in choices]
        l = len(choices)
        assert l > 0
        if l == 2 or choices == [self.root.tx]:
            return choices
        elif l == 1:
            return [choices[0], random.choice([n.tx for n in self.chain.values() if n.tx not in choices])]  # if there's only one frontier node, we select another node at random
        i = j = 0
        while i == j:
            i = random.randint(0, l-1)
            j = random.randint(0, l-1)
        return [choices[i], choices[j]]

    def reachableByAll(self, node):
        """returns whether node is reachable by all frontier nodes that are keys in reachable
        fronts is set of frontier nodes (with front.reachable)
        """
        for front in list(self.front):
            if node not in front.reachable:
                return False
        return True

    def needsReissue(self, node):
        """returns True if both of node's parents are reachableByAll (means node is too deep to be not accepted/reachableByAll itself and needs reissue)
        fronts is list of frontier nodes (with front.reachable)
        """
        for p in node.tx.pointers:
            if not self.reachableByAll(self.chain[p]):  # don't need to worry about excluding node itself
                return False
        return True

    # ==overwritten methods============

    def makeTx(self):
        """return tx
        make sure to append to self.over.allTx
        """
        newtx = tx.Tx(self.over.tick, self.id, self.over.idBag.getNextId())
        parents = self.getNewParents()
        assert parents  # should always have at least one (genesis tx)
        for parent in parents:
            h = parent.hash()
            assert h in self.chain
            newtx.pointers.append(h)
        self.sheep.add(newtx)
        self.over.allTx.append(newtx)
        return newtx

    def checkAll(self):
        """check all nodes for consensus (runs an implicit "tau" on each node, but all at once because it's faster)"""
        self.reissue = set()  # only reset when you checkAll so that it stays full!
        for node in self.chain.values():  # go through all nodes
            if self.reachableByAll(node):
                if node.tx not in self.accepted:
                    node.tx.addEvent(self.over.tick, self.id, tx.State.CONSENSUS)
                    self.accepted.add(node.tx)
                if node.tx.id in self.reissue:
                    self.reissue.remove(node.tx.id)
            else:
                if node.tx in self.accepted:
                    node.tx.addEvent(self.over.tick, self.id, tx.State.DISCONSENSED)
                    self.accepted.remove(node.tx)
                if node.tx in self.sheep and self.needsReissue(node):
                    self.reissue.add(node.tx.id)
