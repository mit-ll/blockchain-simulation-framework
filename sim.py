import sys
import random
import time
import pickle
import networkx as nx
import miner
import overseer
import tx


def setupSim(o):
    """returns graph with Miner objects attached to nodes"""
    # TODO: different topologies
    g = nx.random_geometric_graph(o.numMiners, 0.125)

    if not nx.is_connected(g):  # make sure graph is connected
        return setupSim(o)
    else:
        gen = tx.Tx(-1, None, o.idBag.getNextId())  # genesis tx
        o.allTx.append(gen)
        for i in g.nodes:
            g.nodes[i]['miner'] = o.getMinerClass()(i, gen, g, o)  # include genesis tx
        return g


def runSim(g, o):
    o.tick = 0
    adjs = {}  # cache g.neighbors; REPLACE for dynamic topology!
    while True:
        o.idBag.clear()
        for i in g.nodes:
            if i not in adjs:
                adjs[i] = list(g.neighbors(i))
            g.nodes[i]['miner'].step(adjs[i])  # process messages, populate reissues
        for i in g.nodes:
            g.nodes[i]['miner'].checkReissues()  # add reissues to o.idBag
        for i in g.nodes:
            g.nodes[i]['miner'].postStep(adjs[i])  # if win PoW lottery, gen new tx
        for i in g.nodes:
            g.nodes[i]['miner'].flushMsgs()

        if o.idBag.peekNextId() >= o.maxTx and o.txGenProb > 0:
            o.txGenProb = -1
        anyHaveMsg = bool([True for i in g.nodes if g.nodes[i]['miner'].queue])
        if o.txGenProb <= 0 and not anyHaveMsg:  # run until no miners have messages

            break
        o.tick += 1

# ==REPORTS===========================


def addToTimes(times, miner, t, mx):
    if miner not in times:
        times[miner] = -99
    if t > times[miner]:
        times[miner] = t
    if t > mx:
        mx = t
    return mx


def reports(g, o):
    """populates tx (in o.allTx) with individual report data"""
    allMinerIds = set()
    allMiners = []
    for n in g.nodes:
        m = g.nodes[n]['miner']
        allMinerIds.add(m.id)
        allMiners.append(m)

    disc = []  # disconsensed tx (consensed once, then unconsensed) (may overlap with cons, unc, or other)
    unc = []  # unconsensed tx (consensed by 1 or more but not all miners)
    cons = []  # consensed tx (consensed by all miners) (allTx = cons + unc + other)
    other = []  # not consensed by any miner (different from unconsensed)
    first = {}  # maps id to first isse of that id
    for t in o.allTx:
        if [True for e in t.history if e.state == tx.State.DISCONSENSED]:
            disc.append(t)
        s = set([e.miner for e in t.history if e.state == tx.State.CONSENSUS])
        if not s:  # not consensed by any miner
            other.append(t)
        elif allMinerIds - s:
            unc.append(t)
        else:
            cons.append(t)
        # some preprocessing for the prob. dist. computation
        if t.id not in first:
            first[t.id] = t
        if t.id in first and first[t.id].hash() != t.hash():
            first[t.id].history += t.history  # append tx history to first instance of tx's

    # NOTE: txs with same id are collapsed into the first instance of that id for probability distributions, but not for disconsensed/unconsensed

    seenfirst = set()  # set of tx.ids for which we have handled the original reissued tx and will ignore all other tx with that id
    for x in o.allTx:
        if x.id in seenfirst:
            continue  # these tx will have x.stats = {}
        seenfirst.add(x.id)
        times = {}
        mx = -99
        for e in x.history:
            if e.state == tx.State.CONSENSUS:
                t = e.ts - x.birthday
                mx = addToTimes(times, e.miner, t, mx)
        if mx > 0:  # if mx is still -99, no tx with that id was ever consensed
            x.stats['times'] = times
            x.stats['maxTime'] = mx

    out = {
        'disc': disc,
        'unc': unc,
        'cons': cons,
        'other': other,
        'allTx': o.allTx
    }
    pickle.dump(out, open(o.outFile, 'w'))


if __name__ == "__main__":
    fname = 'sim.json'
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    o = overseer.Overseer(fname)
    print o
    start = time.time()
    g = setupSim(o)
    runSim(g, o)
    print time.time() - start
    reports(g, o)

# Time trials (parens is w/o caching adj)
# Target: 50 tx
# No. of miners:	200	 1000	5000	10000
#  Naive miners:	(7s) (73s)	(6226s)	"Killed"
#  Bitcoin:			9s	 137s			"Killed"
