import hashlib


class Tx:
    def __init__(self, tick, m, i):
        self.origin = m
        self.id = i
        self.birthday = tick
        self.pointers = []  # backpointer(s) are an inherent part of the tx, each miner takes it or leaves it as a whole
        self.history = []  # event history
        self.stats = {}  # filled in after sim for reports

    def hash(self):
        s = ''.join(self.pointers)+str(self.id)+str(self.birthday)+str(self.origin)  # make sure not to include mutable properties like history!
        return hashlib.md5(s).hexdigest()

    def addEvent(self, ts, miner, state):
        self.history.append(Event(ts, miner, state))

    def __str__(self):
        return str(self.id)+' '+str(self.origin)+' '+str(self.birthday)+' '+str(self.pointers)


class Event:
    def __init__(self, ts, miner, state):
        self.ts = ts
        self.miner = miner
        self.state = state


class State:
    UNKNOWN = 0  # not needed; if a miner doesn't show up in a tx's history, it's in this state
    PRE = 1
    CONSENSUS = 2
    DISCONSENSED = 3
