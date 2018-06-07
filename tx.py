import hashlib
class Tx:
	nextId = 0
	def __init__(self,tick,m=None,forceid=None):
		self.origin = m
		if forceid:
			self.id = forceid
		else:
			self.id = Tx.nextId
			Tx.nextId += 1
		self.birthday = tick
		self.pointers = []
		self.history = [] #event history
		self.reissued = False #mark as true if the miner shepherding it finds that it's dead and reissues it.

	#make sure not to include mutable properties like history or reissued
	def hash(self):
		s = ''.join(self.pointers)+str(self.id)+str(self.birthday)+str(self.origin)
		return hashlib.md5(s).hexdigest()

	def addEvent(self,ts,miner,state):
		self.history.append(Event(ts,miner,state))

	def __str__(self):
		return str(self.id)+' '+str(self.origin)+' '+str(self.birthday)+' '+str(self.pointers)+' '+str(self.reissued)

#backpointer is an inherent part of the tx, each miner takes it or leaves it as a whole

class Event:
	def __init__(self,ts,miner,state):
		self.ts = ts
		self.miner = miner
		self.state = state

class State:
	UNKNOWN = 0 #not needed; if a miner doesn't show up in a tx's history, it's in this state
	PRE = 1
	CONSENSUS = 2
	DISCONSENSED = 3
