import traceback
import json
from .signals import PhaseComplete
from .structures import tdict, tset, tlist

class GamePhase(object):
	
	def __init__(self, name=None):
		
		if name is None:
			name = type(self).__name__
		self.name = name
	
	def execute(self, G, player=None, action=None): # must be implemented
		raise NotImplementedError
	
	def encode(self, G): # by default no actions are necessary
		raise PhaseComplete


class EndPhase(GamePhase):
	pass

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


def add_next_phase(G, phase):
	G.game.sequence.insert(G.game.index + 1, phase)

def switch_phase(G, phase):
	G.game.sequence.insert(G.game.index, phase)


def create_gamestate():
	
	G = tdict()
	
	game = tdict()
	game.sequence = tlist()
	game.index = 0
	
	
	
	
	return G
	
	



