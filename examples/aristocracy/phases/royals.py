
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import SwitchPhase, PhaseComplete

# from ..ops import build

class RoyalPhase(GamePhase):
	
	def __init__(self, player, **other):
		super().__init__(player=player, **other)
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			pass
		
		obj, *rest = action
		
	def pre(self):
		raise NotImplementedError
	
	def post(self):
		raise NotImplementedError
		
	def encode(self, C):
		
		out = GameActions('You rolled: {}. Take your turn.'.format(self.roll))
		
		return tdict({self.player:out})


class KingPhase(RoyalPhase):
	def pre(self):
		raise NotImplementedError
	
	def post(self):
		raise NotImplementedError


class QueenPhase(RoyalPhase):
	def pre(self):
		raise NotImplementedError
	
	def post(self):
		raise NotImplementedError


class JackPhase(RoyalPhase):
	def pre(self):
		raise NotImplementedError
	
	def post(self):
		raise NotImplementedError

