import random,tx

class Miner:
	nextId = 0
	def __init__(self,gen,o):
		self.id = Miner.nextId
		Miner.nextId += 1
		self.o = o
		self.preq = [] #to prevent nodes that execute later in a step from acting on msgs from earlier nodes that step
		self.queue = []
		self.seen = set() #set of seen tx HASHES
		self.start(gen) #ABSTRACT - start protocol
		self.hadChangeLastStep = False

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
		return ret #should a miner only receive 1 message at a time, or can it do all at once like this?

	#broadcast message to all adjacent nodes
	def broadcast(self,msg,adj,g):
		for i in adj:
			g.nodes[i]['miner'].pushMsg(msg) #TODO add delay

	def handleTx(self,t,tick,adj,g):
		self.seen.add(t.hash())
		self.broadcast(t,adj,g) #broadcast new/first-time-seen tx (does this ever depend on process()?)
		self.process(tick,t) #ABSTRACT - process tx
	
	#adj is adjacent nodes
	def step(self,tick,adj,g):
		forceSheepCheck = self.hadChangeLastStep
		self.hadChangeLastStep = False
		self.preTick()
		needToCheck = False
		for t in self.popMsg(): #receive message(s) from queue
			if t.hash() in self.seen:
				continue
			needToCheck = True
			self.hadChangeLastStep = True
			self.handleTx(t,tick,adj,g)
		if needToCheck or (self.sheep and forceSheepCheck): #have to check every time if has sheep...
			self.checkAll(tick)
		
		newtx = self.shepherd(tick) #ABSTRACT - check shepherded tx; only gen if not reissuing a sheep
		if not newtx and random.random() < self.o.txGenProb: #chance to gen tx (important that this happens AFTER processing messages)
			newtx = self.makeTx(tick) #ABSTRACT - make a new tx
			self.o.allTx.append(newtx)
		if newtx:
			self.hadChangeLastStep = True
			self.handleTx(newtx,tick,adj,g)
			self.checkAll(tick)

	#==ABSTRACT====================================
	#copy and overwrite these method in subclasses!

	#gen is genesis tx
	def start(self,gen):
		return None

	#get things set up before tick
	def preTick(self):
		return None

	#return tx
	def makeTx(self,tick):
		newtx = tx.Tx(tick)
		return newtx

	#return tx to shepherd, or None if none
	def shepherd(self,tick):
		return None

	#update view
	#run tau-func on all tx
	def process(self,tick,t):
		t.addEvent(tick,self.id,tx.State.CONSENSUS)

	#check all nodes for consensus (calling Tau)
	def checkAll(self,tick):
		return None

#Notes
#How does a miner decide when to reissue shepherded nodes?
#How does a miner know whether a tx its shephering was definitely NOT consensed?
	#Blockchain: another node with the same pointer as the shepherded node is accepted
	#IOTA: ???

