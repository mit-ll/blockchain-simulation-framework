import matplotlib.pyplot as plt

# TODO analyze results of sim
# needs populated o.allTx


def showHist(t):
    """takes a transaction and shows/returns a histogram of how long it took each miner to accept it"""
    if not t.stats:
        return None
    data = t.stats['times'].values()
    plt.hist(data)
    plt.show()
    return data  # maybe just return t.stats['times']?


def showMaxHist(o):
    """shows/returns a histogram of the max time it took each transaction to be accepted by all miners"""
    maxes = [t.stats['maxTime'] for t in o.allTx if t.pointers and t.stats]
    assert maxes
    plt.hist(maxes)  # bins?
    plt.show()
    return maxes


# needs unc,disc,cons, and other from sim.reports
#   if disc:
#        print "Some tx lost consensus after gaining it:", [t.id for t in disc]
#    if unc:
#        print "Consensus has still not been reached for some tx:", [
#            t.id for t in unc]
