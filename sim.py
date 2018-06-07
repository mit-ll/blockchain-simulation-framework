import miner,overseer,plot,tx,bitcoin,random
import networkx as nx

#TODO: different topologies
def makeGraph(o,mclass=miner.Miner):
	#TEST
	if True:#True: # while python sim.py; do :; done
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
		#g=nx.random_lobster(o.numMiners,1,1) # interesting chain-like shape
		#g=nx.wheel_graph(o.numMiners) # most (all?) nodes connected to one node; otherwise connected randomly
	
	if not nx.is_connected(g): #make sure graph is connected
		return makeGraph(o,mclass)
	else:
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
			g.nodes[i]['miner'].flushMsgs() #must be done after all miner.step()
		if len(o.allTx) >= o.maxTx and o.txGenProb > 0:
			o.txGenProb = -1
		anyHaveMsg = bool([True for i in g.nodes if g.nodes[i]['miner'].queue])
		if o.txGenProb <= 0 and not anyHaveMsg: #run until no miners have messages
			break
		tick += 1
		
def addToTimes(times,miner,t,mx):
	if miner not in times:
		times[miner] = -99
	if t > times[miner]:
		times[miner] = t
	if t > mx:
		mx = t
	return mx
	
#TEMP
def printSChain(acc,node,me,t=0):
	i = node.tx.id
	s = '  '*t + str(i)
	if not node.tx.reissued and i in acc:
		s+='*'
	elif node.tx.reissued and node.tx.origin == me:
		s+='-'
	print s
	for c in node.children:
		printSChain(acc,c,me,t+1)

def reports(g,o):
	allMinerIds = set()
	allMiners=[]
	for n in g.nodes:
		m = g.nodes[n]['miner']
		allMinerIds.add(m.id)
		allMiners.append(m)
	#	any disconsensed, ever?
	#	were all nodes consensed (if any node was consensed by one, it must be consensed by all)
	disc = [] # disconsensed tx (consensed once, then unconsensed) (may overlap with cons, unc, or other)
	unc = [] # unconsensed tx (consensed by 1 or more but not all miners)
	cons = [] # consensed tx (consensed by all miners) (allTx = cons + unc + other)
	other = [] # not consensed by any miner (different from unconsensed) or reissued
	for t in o.allTx:
		if [True for e in t.history if e.state == 3]:
			disc.append(t)
		s = set([e.miner for e in t.history if e.state == 2])
		if t.reissued or not s: #not consensed by any miner
			other.append(t)
			continue
		if allMinerIds - s:
			unc.append(t)
		else:
			cons.append(t)
	if disc:
		print "Some tx lost consensus after gaining it:",[t.id for t in disc]
		#TEMP
		m = g.nodes[0]['miner']
		acc = set([t.id for t in m.accepted])
		printSChain(acc,m.root,m.id)
		#TEMP
	if unc:
		print "Consensus has still not been reached for some tx:",[t.id for t in unc]
	#TODO
	#	The simulation will output probability distributions for each transactions. Namely, the time it took for each miner to accept it and the time it took for all miners to accept it.
	for x in o.allTx:
		if x in unc or x in other: # ignore tx that weren't consensed
			#print x.id,'--'
			x.stats['noStats'] = True
			continue
		times = {}
		mx = -99
		for e in x.history:
			t = e.ts - x.birthday
			mx = addToTimes(times,e.miner,t,mx)
		x.stats['noStats'] = False
		x.stats['times'] = times
		x.stats['maxTime'] = mx
		#print x.id,mx
	return

if __name__ == "__main__":
	o = overseer.Overseer()
	g = makeGraph(o,bitcoin.Bitcoin)#g = makeGraph(o)
	#plot.plotGraph(g)
	runSim(g,o)
	reports(g,o)
