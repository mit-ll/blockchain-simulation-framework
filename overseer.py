import json
import random
import bitcoin
import iota


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

    def addId(self, i, miner):
        """miner is miner object, not just id"""
        self.bag.append((i, miner))  # stores id and pointer to miner

    def clear(self):
        """clear at beginning of every tick"""
        self.bag = []


class Overseer:
    """put all settings here; sim.py can initalize/change with .load"""

    def __init__(self):
        self.tick = -1
        self.allTx = []
        self.idBag = IdBag()

        self.protocol = 'bitcoin'
        self.numMiners = 200
        self.txGenProb = .0001667  # once every 10 minutes, assuming 1 tick is 100ms
        self.maxTx = 50
        self.bitcoinAcceptDepth = 6
        self.delayMu = 5
        self.delaySigma = 1.3

    def load(self, fname):
        data = None
        with open(fname, 'r') as f:
            data = json.load(f)
        if not data:
            return
        if 'protocol' in data:
            self.protocol = data['protocol']
        if 'numMiners' in data:
            self.numMiners = data['numMiners']
        if 'txGenProb' in data:
            self.txGenProb = data['txGenProb']
        if 'maxTx' in data:
            self.maxTx = data['maxTx']
        if 'bitcoinAcceptDepth' in data:
            self.bitcoinAcceptDepth = data['bitcoinAcceptDepth']
        if 'delayMu' in data:
            self.delayMu = data['delayMu']
        if 'delaySigma' in data:
            self.delaySigma = data['delaySigma']

    def getMinerClass(self):
        ret = bitcoin.Bitcoin
        if self.protocol == 'iota':
            ret = iota.Iota
        return ret

    def getDelay(self):
        return max(0, round(random.gauss(self.delayMu, self.delaySigma)))

    def __str__(self):
        return "Protocol: "+self.getMinerClass().name+"; Miners: "+str(self.numMiners)+"; Gen. Prob.: "+str(self.txGenProb)+"; MaxTx: "+str(self.maxTx)


# Notes
# Setting message delay in ticks ties ticks to a certain real-world time span
# TODO simulate dropped messages? (how does P2P handle those?)
