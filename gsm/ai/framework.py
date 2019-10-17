
from humpack import Savable, Transactionable
from .. import tlist, tdict, tset

class Agent(tdict):
	
	# Optional override - to use data from current status
	def observe(self, me, table, players, info):
		pass
	
	# Required override - choose from possible actions
	def decide(self, actions):
		raise NotImplementedError
	
	
class RandomAgent(Agent):
	
	def decide(self, actions):
		raise NotImplementedError # TODO


