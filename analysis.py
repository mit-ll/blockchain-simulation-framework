import sys
import pickle
import matplotlib.pyplot as plt
import logging


def showHist(tx):
    """Displays and returns a histogram of how long it took each miner to come to conesensus for a given transaction.

    Arguments:
        tx {Tx} -- Transaction to show histogram for.

    Returns:
        list(int) -- Histogram of how long it took each miner to come to conesensus.
    """

    if not tx.stats:
        return None
    data = tx.stats['times'].values()
    plt.hist(data)
    plt.show()
    return data  # TODO: maybe just return t.stats['times']?


def showMaxHist(allTx):
    """Displays and returns a histogram of the max time it took for consensus to be reached for each transaction in list.

    Arguments:
        allTx {list(Tx)} -- List of tx to generate histogram for.

    Returns:
        list(int) -- Histogram of the max time it took for consensus to be reached for each transaction.
    """

    max_times = [tx.stats['max_time'] for tx in allTx if tx.pointers and tx.stats]
    assert max_times
    plt.hist(max_times)  # TODO: Set bins manually?
    plt.show()
    return max_times


def analyze(fname):
    """Logs a report of the following statistics:
    Whether the simulated protocol was stable (a protocol on a given topology is stable if once a given transaction enters consensus it never leaves consensus).
    Whether the simulated protocol reached eventual consensus (a protocol on a given topology has eventual consensus if all transactions are eventually accepted by the miners in the protocol).
    Probability distributions for each transactions:
        The time it took for each miner to accept it.
        The time it took for all miners to accept it.

    Arguments:
        fname {str} -- File name to read data from.

    Returns:
        dict -- Dictionary of data; see simulation.generateData for contents.
    """

    report = None
    with open(fname) as file:
        report = pickle.load(file)
    if not report:
        return
    disconsensed_tx = report['disconsensed_tx']
    partially_consensed_tx = report['partially_consensed_tx']
    consensed_tx = report['consensed_tx']
    #never_consensed_tx = report['never_consensed_tx']
    all_tx = report['all_tx']

    logging.info("Number of consensed tx: %d" % len(consensed_tx))
    if disconsensed_tx:
        logging.info("Some tx lost consensus after gaining it: %s" % [t.id for t in disconsensed_tx])
    if partially_consensed_tx:
        logging.info("Consensus has still not been reached for some tx: %s" % [t.id for t in partially_consensed_tx])

    # TODO: figure how to log prob dist; write to disk?
    showMaxHist(all_tx)
    return report


if __name__ == "__main__":
    analyze(sys.argv[1])
