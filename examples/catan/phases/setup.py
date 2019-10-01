import numpy as np
from gsm import GamePhase, GameActions, GameOver
from gsm import tset, tdict, tlist


class SetupPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		raise NotImplementedError
	
	def encode(self, C):
		raise NotImplementedError