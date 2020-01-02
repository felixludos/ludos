
from .. import tdict, tlist, tset
from ..mixins import Named
from ..core import GamePhase

class StagePhase(GamePhase):
	def __init__(self, name=None, stages=[]):
		super().__init__(name=name)
		
		self.stage_idx = 0
		self.stages = tlist(stages)
		
	def execute(self, C, player=None, action=None):
		
		# process action
		if action is not None:
			pass
		
		
		
		pass
	
	def encode(self, C):
		
		out = tdict()
		
		
		
		pass
	
	
class Stage(Named, tdict):
	
	def process_action(self, C, player, action):
		return False
	
	def execute(self, C):
		raise NotImplementedError
	


