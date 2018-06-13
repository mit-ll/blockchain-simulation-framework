# put all settings here; sim.py can initalize/change
class IdBag:
    nextId = 0

    def __init__(self):
        self.bag = []  # id queue

    def getNextId(self):
        if self.bag:
            i, miner = self.bag.pop(0)
            miner.removeSheep(i)
            return i
        else:
            ret = IdBag.nextId
            IdBag.nextId += 1
            return ret

    def peekNextId(self):
        if self.bag:
            return self.bag[0][0]
        else:
            return IdBag.nextId

    # miner is miner object, not just id
    def addId(self, i, miner):
        self.bag.append((i, miner))  # stores id and pointer to miner

    # clear at beginning of every tick
    def clear(self):
        self.bag = []


class Overseer:
    tick = -1
    numMiners = 200
    allTx = []
    txGenProb = .0001667  # once every 10 minutes, assuming 1 tick is 100ms
    maxTx = 50
    bitcoinAcceptDepth = 6
    idBag = IdBag()

# Notes
# Setting message delay in ticks ties ticks to a certain real-world time span
# TODO simulate dropped messages? (how does P2P handle those?)
