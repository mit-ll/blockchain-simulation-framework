import random,tx

class Miner:
	nextId = 0
	def __init__(self,o):
		self.id = Miner.nextId
		Miner.nextId += 1
		self.o = o
		self.preq = [] #to prevent nodes that execute later in a step from acting on msgs from earlier nodes that step
		self.queue = []
		self.seen = set() #set of seen tx.id
		#something to store view of blockchain

	#messages are just tx objects
	def pushMsg(self,msg,delay=0):
		self.preq.append([msg,delay])

	def flushMsgs(self):
		self.queue = self.preq[:]
		self.preq = []

	def popMsg(self):
		qcopy = self.queue[:]
		self.queue = []
		ret = []
		for msg,i in qcopy:
			i -=1
			if i<1:
				ret.append(msg)
			else:
				self.pushMsg(msg,i)
		return ret #should a miner only receive 1 message at a time, or can it do all at once?

	#broadcast message to all adjacent nodes
	def broadcast(self,msg,adj,g):
		for i in adj:
			g.nodes[i]['miner'].pushMsg(msg) #what delay to use??
	
	#adj is adjacent nodes
	def step(self,tick,adj,g):
		txs = []
		if random.random() < self.o.txGenProb: #chance to gen tx
			newtx = tx.Tx(tick) #gen tx; TODO need a way to keep track of it, so it doesn't give up
			print 'created tx',newtx.id
			self.o.allTx.append(newtx)
			txs.append(newtx)
		txs += self.popMsg()
		for t in txs: #receive message(s) from queue
			if t.id  in self.seen:
				continue
			self.seen.add(t.id)
			self.broadcast(t,adj,g) #broadcast new/first-time-seen tx
			self.process(tick,t) #process txs (inheritance!)

	#overwrite this method in subclasses!
	def process(self,tick,t):
		t.addEvent(tick,self.id,tx.State.CONSENSUS)
		#update view
		#run tau-func on all tx

