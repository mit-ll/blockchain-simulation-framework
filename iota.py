import random,tx,miner

#node in the bitcoin miner's personal view of the blockchain
class Node:
	def __init__(self,t):
		self.tx = t
		self.children = []
		self.reachable = set() #set of nodes, populate when attaching a new node to its parent's children. Populate with parent and parent's reachable!

class Iota(miner.Miner):
	def __init__(self,i,gen,g,o):
		miner.Miner.__init__(self,i,gen,g,o) #calls self.start()
		self.root = Node(gen)
		self.chain = {} #maps tx hash to nodes whose tx has that hash
		self.chain[gen.hash()] = self.root
		self.accepted = set() #set of tx I've accepted (only used to avoid spamming tx.history events); don't count on this for reporting, use tx.history instead
		self.root.tx.addEvent(-1,self.id,tx.State.CONSENSUS)
		self.accepted.add(self.root.tx)
		self.sheep = set() #queue of tx to shepherd
		self.reissue = set() #temporary set of ids that need to be reissued (populated by checkAll; should be reset every tick)
		self.orphans = []

	#returns the tx from self.chain with the target hash
	def findInChain(self,target):
		if target in self.chain:
			return self.chain[target]
		return None
	
	#TODO: copy this function over bitcoin.Bitcoin's addToChain (it should work there too)
	#t is a tx (with pointer already set), and miner.py has already checked that we haven't seen it
	#returns whether to broadcast tAdd to neighbors
	def addToChain(self,tAdd,sender):
		broadcast = []
		newn = Node(tAdd)
		temp = [newn] + self.orphans[:]
		self.orphans = []
		first = True #this matters for non-orphan-broadcast and for not requesting old orphans from current "sender" who has nothing to do with them
		#if we don't know BOTH of a tx's parents, it's an orphan
		#we don't chain orphans; so during each addToChain we have to try to hookup/mark-as-PRE/add-to-self.chain/broadcast every orphan
		for n in temp: #for new node ("first" is True) and all orphans ("first" is False)
			t = n.tx
			parents = [(self.findInChain(p),p) for p in t.pointers]
			if None not in [p[0] for p in parents]:
				if first:
					broadcast.append(t)
				t.addEvent(self.o.tick,self.id,tx.State.PRE) #note that, contrary to Bitcoin, Iota only marks tx as PRE when its not an orphan...
				self.chain[t.hash()] = n
				for parent,pointer in parents:
					parent.children.append(n)
					n.reachable |= set([parent]) | parent.reachable
			else:
				self.orphans.append(n) #handle orphans as nodes (not just tx) so that we can build orphan chains from them
				if first: #only for new orphan
					assert sender != self.id #if first and sender == self.id, then I'm processing a node I just created and I should never have created an orphan
					for parent,pointer in parents:
						if parent is None:
							self.sendRequest(sender,pointer)
			first = False
		return broadcast
		
	#returns list frontier nodes
	def frontierRec(self,node):
		if not node.children:
			return [node]
		ret = []
		for c in node.children:
			ret += self.frontierRec(c)
		return ret
	
	#returns list of 1 or 2 parent tx for new tx
	def getNewParents(self):
		choices = self.frontierRec(self.root)
		if self.root in choices and len(choices) >= 3:
			choices.remove(self.root)
		choices = [c.tx for c in choices]
		l = len(choices)
		if l < 3:
			return choices
		i=j=0
		while i == j:
			i = random.randint(0,l-1)
			j = random.randint(0,l-1)
		return [choices[i],choices[j]]
		
	#returns whether node is reachable by all frontier nodes that are keys in reachable
	#fronts is list of frontier nodes (with front.reachable)
	def reachableByAll(self,node,fronts):
		for front in fronts:
			if node not in front.reachable:
				return False
		return True
		
	#returns True if both of node's parents are reachableByAll (means node is too deep to be not accepted/reachableByAll itself and needs reissue)
	#fronts is list of frontier nodes (with front.reachable)
	def needsReissue(self,node,fronts):
		return False #TODO; does this function work?
		for p in node.tx.pointers:
			if not self.reachableByAll(self.chain[p],fronts): #don't need to worry about excluding node itself
				return False
		return True

	#==overwritten methods============

	#return tx
	#make sure to append to self.o.allTx
	def makeTx(self):
		newtx = tx.Tx(self.o.tick,self.id,self.o.idBag.getNextId())
		parents = self.getNewParents()
		assert parents #should always have at least one (genesis tx)
		for parent in parents:
			h = parent.hash()
			assert h in self.chain
			newtx.pointers.append(h)
		self.sheep.add(newtx)
		self.o.allTx.append(newtx)
		return newtx

	#a chance for the miner to put its need-to-reissue tx in o.IdBag
	def checkReissues(self):
		for i in self.reissue:
			self.o.idBag.addId(i,self)
		
	#returns whether miner has sheep
	def hasSheep(self):
		if self.sheep:
			return True
		return False

	#update view
	#return True if should broadcast, False otherwise
	def process(self,t,sender):
		return self.addToChain(t,sender)

	#check all nodes for consensus (runs an implicit "tau" on each node, but all at once because it's faster)
	def checkAll(self):
		self.reissue = set() #only reset when you checkAll so that it stays full
		fronts = self.frontierRec(self.root)
		for node in self.chain.values(): #go through all nodes
			if self.reachableByAll(node,fronts):
				if node.tx not in self.accepted:
					node.tx.addEvent(self.o.tick,self.id,tx.State.CONSENSUS)
					self.accepted.add(node.tx)
				if node.tx.id in self.reissue:
					self.reissue.remove(node.tx.id)
			else:
				if node.tx in self.accepted:
					node.tx.addEvent(self.o.tick,self.id,tx.State.DISCONSENSED)
					self.accepted.remove(node.tx)
				if node.tx in self.sheep and self.needsReissue(node,fronts):
					self.reissue.add(node.tx.id)

	#overseer will call this to tell the miner that it doesn't have to shepherd an id anymore
	def removeSheep(self,i):
		x = None
		for s in self.sheep:
			if s.id == i:
				x = s
		if x:
			self.sheep.remove(x)
		if i in self.reissue:
			self.reissue.remove(i)


