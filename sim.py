import miner
import overseer
import plot
import tx
import bitcoin
import random
import math
import time
import iota
import networkx as nx
import matplotlib.pyplot as plt

# TODO: different topologies
# returns graph with Miner objects attached to nodes


def setupSim(o, mclass=miner.Miner):
    # TEST
    if False:  # True: # while python sim.py; do :; done
        degree = random.uniform(.125, .175)
        num = random.randint(o.numMiners, o.numMiners*2)
        # chance = random.uniform(.0001,.001) #this is a pretty huge spread
        mt = random.randint(o.maxTx, o.maxTx*2)
        print "Miners:", num, "; Degree:", degree, "; MaxTx:", mt
        o.maxTx = mt
        g = nx.random_geometric_graph(num, degree)
    else:
        g = nx.random_geometric_graph(o.numMiners, 0.125)
        # g=nx.random_lobster(o.numMiners,1,1) # interesting chain-like shape
        # g=nx.wheel_graph(o.numMiners) # most (all?) nodes connected to one node; otherwise connected randomly

    if not nx.is_connected(g):  # make sure graph is connected
        return setupSim(o, mclass)
    else:
        gen = tx.Tx(-1, None, o.idBag.getNextId())  # genesis tx
        o.allTx.append(gen)
        for i in g.nodes:
            g.nodes[i]['miner'] = mclass(i, gen, g, o)  # include genesis tx
        # populate edges with delays ("weights")?
        return g


def runSim(g, o):
    o.tick = 0
    adjs = {}  # cache g.neighbors; REPLACE for dynamic topology!
    while True:
        # if o.tick % 20 == 0:
        #	print o.tick
        o.idBag.clear()
        for i in g.nodes:
            if i not in adjs:
                adjs[i] = list(g.neighbors(i))
            # process messages, populate reissues
            g.nodes[i]['miner'].step(adjs[i])
        for i in g.nodes:
            g.nodes[i]['miner'].checkReissues()  # add reissues to o.idBag
        for i in g.nodes:
            # if win PoW lottery, gen new tx
            g.nodes[i]['miner'].postStep(adjs[i])
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

# takes a transaction and shows/returns a histogram of how long it took each miner to accept it


def showHist(t):
    if not t.stats:
        return None
    data = t.stats['times'].values()
    plt.hist(data)
    plt.show()
    return data  # maybe just return t.stats['times']?

# shows/returns a histogram of the max time it took each transaction to be accepted by all miners


def showMaxHist(o):
    maxes = [t.stats['maxTime'] for t in o.allTx if t.pointers and t.stats]
    assert maxes
    # ,bins=range(int(math.floor(min(maxes)/10.0))*10,int(math.ceil(max(maxes)/10.0))*10,2))
    plt.hist(maxes)
    plt.show()
    return maxes

# TEMP


def printSChain(node, me, t=0):
    i = node.tx.id
    s = '  '*t + str(i)
    state = 0
    for e in node.tx.history:
        if e.miner == me:
            state = e.state
    if state == 2:  # last state for this miner
        s += "*"
    print s
    for c in node.children:
        printSChain(c, me, t+1)

# populates tx (in o.allTx) with individual report data


def reports(g, o):
    allMinerIds = set()
    allMiners = []
    for n in g.nodes:
        m = g.nodes[n]['miner']
        allMinerIds.add(m.id)
        allMiners.append(m)
    #	any disconsensed, ever?
    #	were all nodes consensed (if any node was consensed by one, it must be consensed by all)
    # disconsensed tx (consensed once, then unconsensed) (may overlap with cons, unc, or other)
    disc = []
    unc = []  # unconsensed tx (consensed by 1 or more but not all miners)
    # consensed tx (consensed by all miners) (allTx = cons + unc + other)
    cons = []
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
            # append tx history to first instance of tx's
            first[t.id].history += t.history
    if disc:
        print "Some tx lost consensus after gaining it:", [t.id for t in disc]
        # TEMP
        m = g.nodes[0]['miner']
        printSChain(m.root, m.id)
        # TEMP
    if unc:
        print "Consensus has still not been reached for some tx:", [
            t.id for t in unc]

    # NOTE: txs with same id are collapsed into the first instance of that id for probability distributions, but not for disconsensed/unconsensed

    #	The simulation will output probability distributions for each transactions. Namely, the time it took for each miner to accept it and the time it took for all miners to accept it.
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
    # showMaxHist(o)


if __name__ == "__main__":
    start = time.time()
    o = overseer.Overseer()
    g = setupSim(o, bitcoin.Bitcoin)  # g = setupSim(o)
    # plot.plotGraph(g)
    runSim(g, o)
    reports(g, o)
    print time.time() - start

# Time trials (parens is w/o caching adj)
# No. of miners:		200	 1000	5000	10000
#  Naive miners:	(7s) (73s)	(6226s)	"Killed"
#  Bitcoin:			9s	 137s			"Killed"
