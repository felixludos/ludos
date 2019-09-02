
from ..containers import tdict, tset, tlist
from .phase import GamePhase
from ..control_flow import create_gamestate
from ..mixins import Named, Typed

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
	
	def create_object(self, **props):
		pass # use table
	
	def save_state(self):
		raise NotImplementedError
	
	def load_state(self):
		raise NotImplementedError


class Player(Named, Typed, tdict):
	def __init__(self, name):
		super().__init__(name, self.__class__.__name__)
