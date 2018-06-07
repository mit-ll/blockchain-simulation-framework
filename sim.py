import miner,overseer,plot,tx,bitcoin,random
import networkx as nx

#TODO: different topologies
def makeGraph(o,mclass=miner.Miner):
	#TEST
	if False:#True: # while python sim.py; do :; done
		degree = random.uniform(.125,.175)
		num = random.randint(o.numMiners,o.numMiners*2)
		chance = random.uniform(.0001,.001)
		mt = random.randint(o.maxTx,o.maxTx*2)
		print "No.:",num,"; Degree:",degree,"; MaxTx:",mt,"; Chance:",chance
		o.txGenProb = chance
		o.maxTx = mt
		g=nx.random_geometric_graph(num,degree)
	else:
		g=nx.random_geometric_graph(o.numMiners,0.125)
	
	g.remove_nodes_from(list(nx.isolates(g))) # connect them randomly instead?
	gen = tx.Tx(-1) #genesis tx
	o.allTx.append(gen)
	for i in g.nodes:
		g.nodes[i]['miner']=mclass(i,gen,g,o) # include genesis tx
	#populate edges with delays ("weights")?
	return g

def runSim(g,o):
	tick = 0
	while True:
		for i in g.nodes:
			node = g.nodes[i]
			node['miner'].step(tick,list(g.neighbors(i)))
		for i in g.nodes:
			g.nodes[i]['miner'].flushMsgs()
		if len(o.allTx) >= o.maxTx and o.txGenProb > 0:
			o.txGenProb = -1
		if o.txGenProb <= 0 and [True for i in g.nodes if g.nodes[i]['miner'].hadChangeLastStep]:#run until no miners had changes last step
			break
		tick += 1

if __name__ == "__main__":
	o = overseer.Overseer()
	g = makeGraph(o,bitcoin.Bitcoin)#g = makeGraph(o)
	#plot.plotGraph(g)
	runSim(g,o)
	#TODO: run reports
	#	any disconsensed, ever?
	#	were all nodes consensed (if any node was consensed by one, it must be consensed by all)
	#		-just ignore reissued? or should I get max ID in o.allTx, and check that some non-reissued tx for each ID from 0 to max from o.allTx was consensed by either all or no miners?
	#	The simulation will output probability distributions for each transactions. Namely, the time it took for each miner to accept it and the time it took for all miners to accept it.
