import hashlib


class Tx:
    def __init__(self, tick, m, i):
        self.origin = m
        self.id = i
        self.birthday = tick
        self.pointers = []
        self.history = []  # event history
        self.stats = {}  # filled in after sim for reports

    # make sure not to include mutable properties like history!
    def hash(self):
        s = ''.join(self.pointers)+str(self.id) + \
            str(self.birthday)+str(self.origin)
        return hashlib.md5(s).hexdigest()

    def addEvent(self, ts, miner, state):
        self.history.append(Event(ts, miner, state))

    def __str__(self):
        return str(self.id)+' '+str(self.origin)+' '+str(self.birthday)+' '+str(self.pointers)

# backpointer is an inherent part of the tx, each miner takes it or leaves it as a whole


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
