
from humpack import Savable, Transactionable
from ..mixins import Named
from ..host import Interface
from .. import tlist, tdict, tset

class Agent(Interface):
	def __init__(self, name=None):
		if name is None:
			name = 'Agent'
		super().__init__(name)
	
	def ping(self):
		return 'ping reply from: {}'.format(self.name)
	
	def step(self, msg):
		raise NotImplementedError # TODO
		
	def reset(self):
		pass
	
	# Optional override - to use data from current status
	def observe(self, me, table, players, info):
		pass
	
	# Required override - choose from possible actions
	def decide(self, actions):
		raise NotImplementedError
	
	
class RandomAgent(Agent):
	
	def decide(self, actions):
		raise NotImplementedError # TODO


