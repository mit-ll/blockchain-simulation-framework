class IdBag:
    """Manages which transaction id should be issued next. Holds a queue of tx ids that need to be reissued.
    """

    def __init__(self, simulation):
        """[summary]

        Arguments:
            simulation {Simulation} -- Simulation that the bag will be used in (referenced for next_id when bag is empty).
        """

        self.simulation = simulation
        self.bag = []  # Id queue.

    def getNextId(self):
        """
        Returns:
            int -- Next tx id that should be used. From the queue of reissued ids, or a new one if the queue is empty.
        """

        if self.bag:
            tx_id, miner = self.bag.pop(0)
            miner.removeSheep(tx_id)
            return tx_id
        else:
            return_id = self.simulation.next_id
            self.simulation.next_id += 1
            return return_id

    def addId(self, tx_id, miner):
        """Adds an id to the bag's queue to be reissued.

        Arguments:
            tx_id {int} -- Id to be reiussed.
            miner {Miner} -- Miner who is shepherding that id.
        """

        self.bag.append((tx_id, miner))  # Stores id and pointer to miner.

    def clear(self):
        """Emtpy the bag of ids.
        """

        self.bag = []


singleton = None


def getSingleBag(simulation):
    """
    Arguments:
        simulation {Simulation} -- Simulation that the bag will be used in.

    Returns:
        IdBag -- A singleton IdBag object.
    """

    global singleton
    if singleton is None:
        singleton = IdBag(simulation)
    return singleton
