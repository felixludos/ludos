import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset

from .phases import TurnPhase

class TicTacToe(gsm.GameController):
	
	def __init__(self, debug=False):
		super().__init__(debug)
		
		# register config files
		self.register_config('basic', 'config/basics.yaml')
		
		# register players
		self.register_player('Player1', val=1)
		self.register_player('Player2', val=-1)
		
		# register game object types
		self.register_obj_type(name='tick',
		                       required={'row', 'col',
		                                 'symbol', 'player'},
		                       visible={'row', 'col', # all properties are always visible to all players -> full information game
		                                'symbol', 'player'}
		                       )
		
		# register possible phases
		self.register_phase(name='turn', cls=TurnPhase)
	
	def _set_phase_stack(self, config):
		
		return tlist([self._get_phase('turn')()])
	
	def _init_game(self, config):
		
		# update player props
		
		self.players[0].symbol = config.basic.characters.p1
		self.players[1].symbol = config.basic.characters.p2
		
		# init state
		
		side = config.basic.side_length
		
		self.state.map = np.zeros((side, side), dtype=int)
		
		self.state.turn_counter = 0
		
	def _end_game(self):
		
		val = self.state.winner
		
		if val is None:
			return tdict(winner=None)
		
		for p in self.players:
			if p.val == val:
				return tdict(winner=p.name)
			
		raise Exception('No player with val: {}'.format(val))