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
	def __init__(self,i,gen,g,o):
		miner.Miner.__init__(self,i,gen,g,o) #calls self.start()
		self.root = Node(gen)
		self.chain = set() #set of nodes (a second pointer into the chain for when you need to find a node with a tx that has a certain hash)
		self.chain.add(self.root)
		self.accepted = set() #set of tx I've accepted. WARNING: don't count on this for reporting; use tx history instead
		self.root.tx.addEvent(-1,self.id,tx.State.CONSENSUS)
		self.accepted.add(self.root.tx)
		self.sheep = [] #queue of tx to shepherd
		self.reissue = [] #temporary ordered list of tx that need to be reissued (populated by checkAll; should be reset every tick)
		self.orphans = []

	#returns the tx from self.chain with the target hash
	def findInChain(self,target):
		for n in self.chain:
			if target == n.tx.hash():
				return n
		return None

	#t is a tx (with pointer already set), and miner.py has already checked that we haven't seen it
	def addToChain(self,tAdd,tick,sender):
		#from bitcoin wiki (https://en.bitcoin.it/wiki/Protocol_rules):
		#	add this to orphan blocks, then query peer we got this from for 1st missing orphan block in prev chain; done with block
		#	(also, when handling orphan blocks:) For each orphan block for which this block is its prev, run all these steps (including this one) recursively on that orphan
		#keep list of orphan nodes, still put them in self.chain so we have pointers to them, and whenever we get a new node, check orphans to see if it fits!
		newn = Node(tAdd)
		self.chain.add(newn)
		temp = [newn] + self.orphans[:]
		self.orphans = []
		first = True #this matters for non-orphan-broadcast and for not requesting old orphans from current "sender" who has nothing to do with them
		for n in temp: #for new node ("first" is True) and all orphans ("first" is False)
			t = n.tx
			parent = self.findInChain(t.pointers[0]) #only ever one pointer in Bitcoin
			if first:
				broadcast = self.findInChain(tAdd.pointers[0]) is not None #do not broadcast orphans
				t.addEvent(tick,self.id,tx.State.PRE) #putting this here means that orphans are marked PRE before they join the genesis-rooted tree
			if parent is None:
				#handle orphans as nodes (not just tx) so that we can build orphan chains from them
				self.orphans.append(n)
				if first: #only for new orphan
					assert sender != self.id
					self.sendRequest(sender,t.pointers[0])
			else:
				parent.children.append(n)
		#(Being a sheep and being an orphan are mutually exclusive; new nodes are added to originator's view, rooted at the genesis block)
			first = False
		return broadcast

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
				node.tx.addEvent(tick,self.id,tx.State.CONSENSUS)
				self.accepted.add(node.tx)
			elif mx != maxDepth:
				if node.tx in self.accepted:
					node.tx.addEvent(tick,self.id,tx.State.DISCONSENSED)
					self.accepted.remove(node.tx)
				#below:first condition says that it's a sheep on an unaccepted fork, second condition says whether it's time to rebroadcast (~"trunk" is 6+ deep)
				if node.tx in self.sheep and mx < maxDepth - self.o.bitcoinAcceptDepth:
					self.reissue.append(node.tx) #the order these will be added to reissue is leaf-up

		return mx

	#==overwritten methods============

	#get things set up before tick
	def preTick(self):
		self.reissue = []

	#return tx
	#make sure to append to self.o.allTx
	def makeTx(self,tick,forceid=None):
		newtx = tx.Tx(tick,self.id,forceid)
		deepest = deepestChildren(self.root)
		parent = random.choice(deepest)
		newtx.pointers.append(parent.tx.hash())
		self.sheep.append(newtx)
		self.o.allTx.append(newtx)
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
		
	#returns whether miner has sheep
	def hasSheep(self):
		if self.sheep:
			return True
		return False

	#update view
	#run tau-func on all tx
	#return True if should broadcast, False otherwise
	def process(self,tick,t,sender):
		return self.addToChain(t,tick,sender)

	#check all nodes for consensus (runs an implicit "tau" on each node, but all at once because it's faster)
	def checkAll(self,tick):
		maxDepth = self.checkRec(self.root,tick)
		if maxDepth < self.o.bitcoinAcceptDepth:
			return
		self.checkRec(self.root,tick,maxDepth)

	

