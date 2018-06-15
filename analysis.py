import sys
import pickle
import matplotlib.pyplot as plt


def showHist(t):
    """takes a transaction and shows/returns a histogram of how long it took each miner to accept it"""
    if not t.stats:
        return None
    data = t.stats['times'].values()
    plt.hist(data)
    plt.show()
    return data  # maybe just return t.stats['times']?


def showMaxHist(allTx):
    """shows/returns a histogram of the max time it took each transaction to be accepted by all miners"""
    maxes = [t.stats['maxTime'] for t in allTx if t.pointers and t.stats]
    assert maxes
    plt.hist(maxes)  # bins?
    plt.show()
    return maxes


# TODO analyze results of sim
def analyze(fname):
    report = None
    with open(fname) as fp:
        report = pickle.load(fp)
    if not report:
        return
    disc = report['disc']
    unc = report['unc']
    cons = report['cons']
    other = report['other']
    allTx = report['allTx']
    if disc:
        print "Some tx lost consensus after gaining it:", [t.id for t in disc]
    if unc:
        print "Consensus has still not been reached for some tx:", [t.id for t in unc]
    return report  # showMaxHist(allTx)


if __name__ == "__main__":
    analyze(sys.argv[1])
