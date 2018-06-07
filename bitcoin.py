import random,tx,miner

#debug
def printChain(node,acc=None,t=0):
	s = '  '*t+str(node.tx.id)
	if acc and node.tx in acc:
		s+='*'
	print s
	for c in node.children:
		printChain(c,acc,t+1)

#not used
def height(node):
	return deepRec(node)[1]

def deepestChildren(node):
	return deepRec(node)[0]

def deepRec(node,d=0):
	if not node.children:
		return [node],d
	l = []
	mx = 0
	for c in node.children:
		subl,subd = deepRec(c,d+1)
		if subd > mx:
			l = []
			mx = subd
		if subd == mx:
			l += subl
	return l,mx	

#node in the bitcoin miner's personal view of the blockchain
class Node:
	def __init__(self,t):
		self.tx = t
		self.children = []

class Bitcoin(miner.Miner):
	def __init__(self,gen,o):
		miner.Miner.__init__(self,gen,o)
		#calls self.start()

	#returns the tx from self.chain with the target hash
	def findInChain(self,target):
		for n in self.chain:
			if target == n.tx.hash():
				return n
		return None

	#t is a tx (with pointer already set)
	def addToChain(self,t,tick):
		parent = self.findInChain(t.pointers[0]) #only ever one pointer in BC
		if parent is None: #hasn't seen preceding node! TODO look up what to do on Bitcoin Wiki
			assert False
		t.addEvent(tick,self.id,tx.State.PRE)
		newn = Node(t)
		parent.children.append(newn)
		self.chain.add(newn)

	#returns maxDepth
	#if maxDepth is > 0, will mark tx as accepted if they are in the deepest chain and at least 6 deep
	def checkRec(self,node,tick,maxDepth=-99,d=0):
		if not node.children:
			if node.tx in self.sheep and d < maxDepth - self.o.bitcoinAcceptDepth:
				self.reissue.append(node.tx)
			return d
		mx = 0
		for c in node.children:
			i = self.checkRec(c,tick,maxDepth,d+1)
			if i > mx:
				mx = i

		if maxDepth > 0:
			if mx == maxDepth and mx - d >= self.o.bitcoinAcceptDepth and node.tx not in self.accepted:
				#if [e for e in node.tx.history if e.miner == self.id][-1].state == tx.State.DISCONSENSED:
				#	print node.tx.id,"reconsensed after disconsensed by",self.id
				node.tx.addEvent(tick,self.id,tx.State.CONSENSUS)
				self.accepted.add(node.tx)
			elif mx != maxDepth:
				if node.tx in self.accepted:
					#print node.tx.id,'DISCONSENSED by',self.id
					#if self.id == 0:
					#	printChain(self.root,self.accepted)
					#	print '--------------------\n'
					node.tx.addEvent(tick,self.id,tx.State.DISCONSENSED)
					self.accepted.remove(node.tx)
				#below:first condition says that it's a sheep on an unaccepted fork, second condition says whether it's time to rebroadcast (~"trunk" is 6+ deep)
				if node.tx in self.sheep and mx < maxDepth - self.o.bitcoinAcceptDepth:
					self.reissue.append(node.tx) #the order these will be added to reissue is leaf-up

		return mx

	#==overwritten methods============

	#gen is genesis transaction
	def start(self,gen):
		self.root = Node(gen)
		self.chain = set() #set of nodes (a second pointer into the chain for when you need to find a node with a tx that has a certain hash)
		self.chain.add(self.root)
		self.accepted = set() #set of tx I've accepted
		self.accepted.add(self.root.tx)
		self.sheep = [] #queue of tx to shepherd
		self.reissue = [] #temporary ordered list of tx that need to be reissued (populated by checkAll; should be reset every tick)

	#get things set up before tick
	def preTick(self):
		self.reissue = []

	#return tx
	def makeTx(self,tick,forceid=None):
		newtx = tx.Tx(tick,self.id,forceid)
		deepest = deepestChildren(self.root)
		#if len(deepest) > 1:
		#	print "I see a fork!" #just curious
		#	printChain(self.root)
		#	print "---------------\n"
		parent = random.choice(deepest)
		newtx.pointers.append(parent.tx.hash())
		self.sheep.append(newtx)
		return newtx

	#How BITCOIN miners handle shepherding
	#checkall, which should also mark nodes as need-to-reissue
	#for each sheep in self.sheep, if that node is marked; set the first one as newTx
	#else, chance to make newTx
	#if newTx, handle and checkall (exact same as above, if any are marked as need-to-reissue, then they will still be marked next step if no msgs)

	#return tx to shepherd, or None if none
	def shepherd(self,tick):
		if not self.reissue:
			return None
		deadTx = self.reissue[0]
		self.sheep.remove(deadTx)
		deadTx.reissued = True
		return self.makeTx(tick,deadTx.id)

	#update view
	#run tau-func on all tx
	def process(self,tick,t):
		self.addToChain(t,tick)

	#check all nodes for consensus (runs an implicit "tau" on each node, but all at once because it's faster)
	def checkAll(self,tick):
		maxDepth = self.checkRec(self.root,tick)
		if maxDepth < self.o.bitcoinAcceptDepth:
			return
		self.checkRec(self.root,tick,maxDepth)

	

