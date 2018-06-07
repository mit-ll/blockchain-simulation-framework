import random,tx

class Message:
	def __init__(self,s,t,c):
		self.sender = s
		self.type = t
		self.content = c

class Type:
	BLOCK = 0
	REQUEST = 1

class Miner:
	nextId = 0
	def __init__(self,i,gen,g,o):
		self.id = i
		#Miner.nextId += 1
		self.g = g
		self.o = o
		self.preq = [] #to prevent miners that execute later in a step from acting on msgs from miners that executed earlier that step
		self.queue = []
		self.seen = {} #dictionary mapping hash to tx for seen tx
		self.seen[gen.hash()] = gen
		self.hadChangeLastStep = False

	#msg is Message object
	def pushMsg(self,msg,delay=0):
		assert type(msg) != str
		self.preq.append([msg,delay])

	def flushMsgs(self):
		self.queue = self.preq[:]
		self.preq = []

	def popMsg(self):
		qcopy = self.queue[:]
		self.queue = []
		ret = []
		for msg,i in qcopy:
			i -= 1
			if i<1:
				ret.append(msg)
			else:
				self.pushMsg(msg,i)
		return ret #should a miner only receive 1 message at a time, or can it do all at once like this?

	#broadcast tx to all adjacent miners
	def broadcast(self,adj,t):
		for i in adj:
			self.sendMsg(i,Message(self.id,Type.BLOCK,t))

	def sendMsg(self,recipient,msg):
	
		#DEBUG
		if msg.type == Type.BLOCK and set(msg.content.pointers) - set(self.seen):
			diff = list(set(msg.content.pointers) - set(self.seen))
			print self.id,"is sending",msg.content.id,"to",recipient,"but it hasn't seen hash(es):",diff
			print "Unhashed pointer(s):"
			for targetHash in diff:
				for t in self.o.allTx:
					if t.hash() == targetHash:
						print targetHash,"->",t.id,t.origin,t.birthday,t.pointers
			assert False
			
		self.g.nodes[recipient]['miner'].pushMsg(msg,random.randint(0,10)) #TODO parameterize delay

	#so subclasses don't have to know about Message/Type classes
	def sendRequest(self,recipient,targetHash):
		self.sendMsg(recipient,Message(self.id,Type.REQUEST,targetHash))

	def handleTx(self,t,sender,adj):
		self.seen[t.hash()] = t
		if self.process(t,sender): #ABSTRACT - process tx
			self.broadcast(adj,t) #broadcast new/first-time-seen-NOT-ORPHAN tx only
	
	#adj is adjacent miners
	def step(self,adj):
		forceSheepCheck = self.hadChangeLastStep
		self.hadChangeLastStep = False
		needToCheck = False
		for msg in self.popMsg(): #receive message(s) from queue
			if msg.type == Type.BLOCK:
				t = msg.content
				if t.hash() in self.seen:
					continue
				needToCheck = True
				self.hadChangeLastStep = True
				self.handleTx(t,msg.sender,adj)
			elif msg.type == Type.REQUEST: #requests are issued by other miners
				targetHash = msg.content

				#DEBUG
				if targetHash not in self.seen:
					print self.id,"doesn't know hash",targetHash,"requested by",msg.sender,"on step",self.o.tick
					print "Unhashed target:"
					for t in self.o.allTx:
						if t.hash() == targetHash:
							print t.id,t.origin,t.birthday,t.pointers
					assert False #currently should NEVER get here; should be caught in assertFalse in DEBUG section of sendMsg
				
				requestedTx = self.seen[targetHash] #if it isn't there, there's a problem
				self.sendMsg(msg.sender,Message(self.id,Type.BLOCK,requestedTx))
		if needToCheck or (self.hasSheep() and forceSheepCheck): #have to check every time if has sheep...
			self.checkAll()
			
	def postStep(self,adj):
		if random.random() < self.o.txGenProb: #chance to gen tx (important that this happens AFTER processing messages)
			newtx = self.makeTx() #ABSTRACT - make a new tx
			self.hadChangeLastStep = True
			self.handleTx(newtx,self.id,adj)
			self.checkAll()

	#==ABSTRACT====================================
	#copy and overwrite these method in subclasses!

	#return tx
	#make sure to append to self.o.allTx
	def makeTx(self):
		newtx = tx.Tx(self.o.tick,self.id,self.o.idBag.getNextId())
		self.o.allTx.append(newtx)
		return newtx

	#a chance for the miner to put its need-to-reissue tx in o.IdBag
	def checkReissues(self):
		return None
		
	#returns whether miner has sheep
	def hasSheep(self):
		return False

	#update view
	#run tau-func on all tx
	#return True if should broadcast, False otherwise
	def process(self,t,sender):
		t.addEvent(self.o.tick,self.id,tx.State.CONSENSUS)
		return True

	#check all nodes for consensus (calling Tau)
	def checkAll(self):
		return None
		
	#overseer will call this to tell the miner that it doesn't have to shepherd an id anymore
	def removeSheep(self,i):
		return None

