from collections import defaultdict
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import os

from json_endec import GraphDecoder


def plotCDF(data):
    plt.plot(np.sort(data), np.linspace(0, 1, len(data), endpoint=False))


def showMultiCDF(run_results, exclude_genesis=True):
    """Displays overlaid CDFs of the max time it took for consensus to be reached for each transaction the results of one run.

    Arguments:
        run_results {dict} -- Dictionary mapping tx id to list of times it took for miners to reach consensus for that tx.

    Keyword Arguments:
        exclude_genesis {bool} -- Whether to exclude the genesis tx. (default: {True})
    """

    for tx_id in run_results:
        if exclude_genesis and tx_id == 0:
            continue
        plotCDF(run_results[tx_id]['times'])
    plt.show()


def showTotalCDF(data, exclude_genesis=True):
    """Displays an aggregate CDF of the max time it took for consensus to be reached for every transaction in a set of results.

    Arguments:
        data {list((networkx.Graph, dict))} -- Output of loadData below.

    Keyword Arguments:
        exclude_genesis {bool} -- Whether to exclude the genesis tx. (default: {True})
    """

    all_times = []
    for run in data:
        run_results = run[1]
        for tx_id in run_results:
            if exclude_genesis and tx_id == 0:
                continue
            all_times += run_results[tx_id]['times']  # Combines all histogram data into one.
    plotCDF(all_times)
    plt.show()


def reportDisconsensed(data):
    """Reports on which transactions were in consensus and left it during the simulation.

    Arguments:
        data {list((networkx.Graph, dict))} -- Output of loadData below.
    """

    tx_count = 0
    disc_count = 0
    became_disc_times = set()
    disc_lasted_durations = []
    for run in data:
        run_results = run[1]
        for tx_id in run_results:
            tx_count += 1
            counted = False
            for disc in run_results[tx_id]['disconsensed']:
                if not counted:
                    disc_count += 1
                    counted = True
                became_disc_times.add(disc[0])
                if disc[1] != -1:  # Don't count disc durations if tx hadn't become consensed again before sim finished.
                    disc_lasted_durations.append(disc[1])
    if disc_count == 0:
        logging.info("No nodes were disconsensed!")
        return None
    logging.info("%d out of %d tx disconsensed." % (disc_count, tx_count))
    percent = disc_count / float(tx_count)
    logging.info("Chance to be disconsensed: %f" % percent)
    plotCDF(list(became_disc_times))
    plt.show()
    plotCDF(disc_lasted_durations)
    plt.show()
    return tx_count, disc_count, list(became_disc_times), disc_lasted_durations


def timeBetweenTx(data):
    """Returns a list of the number of elapsed ticks between each created transaction.

    Arguments:
        data {list((networkx.Graph, dict))} -- Output of loadData below.
    """

    between = []
    for run in data:
        run_results = run[1]
        last = 0
        for created in sorted([run_results[tx_id]['created'][0] for tx_id in run_results]):
            if created < 0:
                continue
            assert created > last, "created: %d; last: %d" % (created, last)
            between.append(created-last)
            last = created
    return between

#r is data[i][1]


def showAllConfidencePlots(r):
    bad = set()
    for i in r:
        c = r[i]['confidences']
        for m in c:
            for v in c[m][1]:
                if v < 100:
                    bad.add(i)
                    break
    for i in bad:
        c = r[i]['confidences']
        for m in c:
            plt.plot(c[m][0], c[m][1])
        plt.show()


def loadData(data_dir='./out/'):
    """Loads data from files in data_dir into a list of dictionaries mapping tx id to list of times it took for miners to reach consensus for that tx, one dict for each run.

    Arguments:
        data_dir {str} -- Directory where data files should be loaded from.

    Returns:
        {list((networkx.Graph, dict))} -- List of (graph, dictionary) tuples--one tuple for each run--in which the dictionary maps tx id to a (event, list) tuple of the tx's creation and times it took for miners to reach consensus for that tx.
    """

    raw_data = []
    for fname in os.listdir(data_dir):
        if not fname.endswith('.json'):
            continue
        with open(data_dir+fname, 'r') as infile:
            raw_data.append(json.load(infile, cls=GraphDecoder))
    if not raw_data:
        return

    data = []
    for run in raw_data:
        run_results = defaultdict(dict)
        for tx_id_str in run['tx_histories']:
            history = run['tx_histories'][tx_id_str]
            tx_id = int(tx_id_str)
            max_times = defaultdict(int)
            last_disc = -1
            disconsensed = []
            created = None
            for event in history:  # Event is [time_step, miner_id, transaction.State].
                if event[2] == 'CREATED':
                    created = event
                    continue
                elif event[2] == 'DISCONSENSED':
                    assert created is not None
                    disconsensed.append([event[0] - created[0], -1])
                    last_disc = event[0]
                    continue
                elif event[2] != 'CONSENSUS':
                    continue
                if last_disc > 0:
                    if event[0] > last_disc:  # Sequence of chronologically ordered events is broken when another history is appended.
                        disconsensed[-1][1] = event[0] - last_disc
                    last_disc = -1
                elapsed = event[0] - created[0]
                if max_times[event[1]] < elapsed:
                    max_times[event[1]] = elapsed
            confidence_history = run['tx_confidence_histories'][tx_id_str]
            confidences = defaultdict(lambda: ([], []))
            for event in confidence_history:
                confidences[event[1]][0].append(event[0])
                confidences[event[1]][1].append(event[2])
            run_results[tx_id]['confidences'] = confidences
            run_results[tx_id]['created'] = created
            run_results[tx_id]['times'] = max_times.values()
            run_results[tx_id]['disconsensed'] = disconsensed
        data.append((run['graph'], run_results))
    return data
