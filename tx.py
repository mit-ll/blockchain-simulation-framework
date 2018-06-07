class Tx:
	nextId = 0
	def __init__(self,tick):
		self.id = Tx.nextId
		Tx.nextId += 1
		self.birthday = tick
		self.pointers = []
		self.history = [] #event history

	def addEvent(self,ts,miner,state):
		self.history.append(Event(ts,miner,state))

class Event:
	def __init__(self,ts,miner,state):
		self.ts = ts
		self.miner = miner
		self.state = state

class State:
	UNKNOWN = 0 #not needed; if a miner doesn't show up in a tx's history, it's in this state
	PRE = 1
	CONSENSUS = 2
