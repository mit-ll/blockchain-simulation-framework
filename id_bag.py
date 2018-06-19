class IdBag:
    def __init__(self, simulation):
        self.simulation = simulation
        self.bag = []  # id queue

    def getNextId(self):
        if self.bag:
            i, miner = self.bag.pop(0)
            miner.removeSheep(i)
            return i
        else:
            return_id = self.simulation.next_id
            self.simulation.next_id += 1
            return return_id

    def addId(self, i, miner):
        self.bag.append((i, miner))  # stores id and pointer to miner

    def clear(self):
        self.bag = []


single = None


def getSingleBag(simulation):
    global single
    if single is None:
        single = IdBag(simulation)
    return single
