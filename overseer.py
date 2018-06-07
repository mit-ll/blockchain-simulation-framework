#put all settings here; sim.py can initalize/change
class IdBag: #problem with this is when to clear or remove sheep that are reconsensed...
	nextId = 0
	def __init__(self):
		self.bag = []#only store ids
		
	def getNextId(self):
		if self.bag:
			return self.bag.pop(0)
		ret = TxIdBag.nextId
		IdBag.nextId += 1
		return ret
		
	def addId(self,i):
		self.bag.append(i)

	def clear(self):
		self.bag = []

class Overseer:
	numMiners = 200
	allTx = []
	txGenProb = .0001667 #once every 10 minutes, assuming 1 tick is 100ms
	maxTx = 50
	bitcoinAcceptDepth = 6
	idBag = IdBag()

#Notes
#Setting message delay in ticks ties ticks to a certain real-world time span
#TODO simulate dropped messages? (how does P2P handle those?)
