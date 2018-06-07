import miner,overseer
import networkx as nx

#TODO: different topology
def makeGraph(o):
	g=nx.random_geometric_graph(200,0.125)
	for i in g.nodes:
		g.nodes[i]['miner']=miner.Miner(o)
	#populate edges with delays ("weights")?
	return g

def runSim(g,o):
	tick = 0
	end = 1000000
	while True:
		if tick % 100 == 0:
			print tick
		for i in g.nodes:
			node = g.nodes[i]
			node['miner'].step(tick,list(g.neighbors(i)),g)
		for i in g.nodes:
			g.nodes[i]['miner'].flushMsgs()
		#terminate after N tx are created?
		if len(o.allTx) > 99 and o.txGenProb > 0:
			o.txGenProb = -1
			end = tick+10
		if tick > end:
			break
		tick += 1

if __name__ == "__main__":
	o = overseer.Overseer()
	g = makeGraph(o)
	runSim(g,o)
