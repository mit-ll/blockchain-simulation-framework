#put all settings here; sim.py can initalize/change
class Overseer:
	numMiners = 200
	allTx = []
	txGenProb = .0001
	maxTx = 50
	bitcoinAcceptDepth = 6

#Notes
#Setting message delay in ticks ties ticks to a certain real-world time span
#If we add chance to drop messages, we also need some kind of re-broadcast/gossip!
