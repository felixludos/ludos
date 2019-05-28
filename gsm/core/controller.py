
from .phase import GamePhase

class GameController(object):
	
	def __init__(self, gamestate=None):
		if gamestate is None:
			gamestate = create_gamestate()
		self.phases = {}
		self.gamestate = gamestate
	
	def register_phase(self, phase):
		assert isinstance(phase, GamePhase), 'Not a GamePhase instance'
		
		self.phases[phase.name] = phase
	
	def reset(self, player):
		raise NotImplementedError
	
	def step(self, player, action):
		raise NotImplementedError
	
	def get_info(self, player):
		raise NotImplementedError
	
	def get_table(self, player):
		raise NotImplementedError
	
	
	
	
	def save_state(self):
		raise NotImplementedError
	
	def load_state(self):
		raise NotImplementedError
