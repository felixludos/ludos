
from .phase import GamePhase
from ..control_flow import create_gamestate

class GameController(object):
	
	def __init__(self):
		self.phases = {}
		self.gamestate = None
	
	def register_phase(self, phase):
		assert isinstance(phase, GamePhase), 'Not a GamePhase instance'
		
		self.phases[phase.name] = phase
	
	def reset(self, player, seed=None):
		
		self.gamestate = create_gamestate()
		
		
		
		raise NotImplementedError
	
	def step(self, player, action):
		raise NotImplementedError
	
	def get_info(self, player):
		raise NotImplementedError
	
	def get_table(self, player):
		raise NotImplementedError
	
	def get_log(self, player):
		raise NotImplementedError
	
	
	def save_state(self):
		raise NotImplementedError
	
	def load_state(self):
		raise NotImplementedError
