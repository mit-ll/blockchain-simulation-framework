from collections import defaultdict
import json
import matplotlib.pyplot as plt
import numpy as np
import os

from json_endec import GraphDecoder


def plotCDF(data):
    plt.plot(np.sort(data), np.linspace(0, 1, len(data), endpoint=False))


def showMultiCDF(run, exclude_genesis=True):
    """Displays overlaid CDFs of the max time it took for consensus to be reached for each transaction the results of one run.

    Arguments:
        run {dict} -- Dictionary mapping tx id to list of times it took for miners to reach consensus for that tx.

    Keyword Arguments:
        exclude_genesis {bool} -- Whether to exclude the genesis tx. (default: {True})
    """

    for tx_id in run:
        if exclude_genesis and tx_id == 0:
            continue
        plotCDF(run[tx_id])
    plt.show()


def showTotalCDF(results, exclude_genesis=True):
    """Displays an aggregate CDF of the max time it took for consensus to be reached for every transaction in a set of results.

    Arguments:
        results {list(dict)} -- List of dictionaries mapping tx id to list of times it took for miners to reach consensus for that tx, one dict for each run.

    Keyword Arguments:
        exclude_genesis {bool} -- Whether to exclude the genesis tx. (default: {True})
    """

    all_times = []
    for run in results:
        for tx_id in run:
            if exclude_genesis and tx_id == 0:
                continue
            all_times += run[tx_id]
    plotCDF(all_times)
    plt.show()


def analyze(data_dir):
    data = []
    for fname in os.listdir(data_dir):
        with open(data_dir+fname, 'r') as infile:
            data.append(json.load(infile, cls=GraphDecoder))
    if not data:
        return

    results = []
    for run in data:
        run_results = {}
        for tx_id_str in run['tx_histories']:
            history = run['tx_histories'][tx_id_str]
            tx_id = int(tx_id_str)
            max_times = defaultdict(int)
            birthday = None
            for event in history:  # Event is [time_step, miner_id, transaction.State].
                if event[2] == 'CREATED':
                    birthday = event[0]
                    continue
                if event[2] != 'CONSENSUS':
                    continue
                elapsed = event[0] - birthday
                if max_times[event[1]] < elapsed:
                    max_times[event[1]] = elapsed
            run_results[tx_id] = max_times.values()
        results.append(run_results)
    return results
