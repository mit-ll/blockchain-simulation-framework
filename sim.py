import miner,overseer,plot,tx
import networkx as nx

#TODO: different topologies
def makeGraph(o,mclass=miner.Miner):
	g=nx.random_geometric_graph(o.numMiners,0.125)
	g.remove_nodes_from(list(nx.isolates(g))) # this is fine, right?
	gen = tx.Tx(-1)
	for i in g.nodes:
		g.nodes[i]['miner']=mclass(gen,o) # include genesis node
	#populate edges with delays ("weights")?
	return g

def runSim(g,o):
	tick = 0
	end = 1000000
	while True:
		#if tick % 500 == 0:
		#	print tick
		for i in g.nodes:
			node = g.nodes[i]
			node['miner'].step(tick,list(g.neighbors(i)),g)
		for i in g.nodes:
			g.nodes[i]['miner'].flushMsgs()
		if len(o.allTx) >= o.maxTx and o.txGenProb > 0:
			o.txGenProb = -1
			end = tick + 100 #TODO: ask each miner if they are still trying to get a tx approved!
		if tick > end:
			break
		tick += 1

if __name__ == "__main__":
	o = overseer.Overseer()
	g = makeGraph(o)
	plot.plotGraph(g)
	runSim(g,o)

