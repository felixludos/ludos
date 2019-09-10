import sys, os
import gsm
from gsm import tdict, tlist, tset

from .phases import TurnPhase

class TicTacToe(gsm.GameController):
	
	def __init__(self, debug=False):
		super().__init__(debug)
		
		# register config files
		self.register_config('basic', 'config/basics.yaml')
		
		# register game object types
		self.register_obj_type(name='tick',
		                       required={'row', 'col',
		                                 'symbol', 'player'},
		                       visible={'row', 'col', # all properties are always visible to all players -> full information game
		                                'symbol', 'player'})
		
		# register phases
		self.register_phase(name='turn', cls=TurnPhase)
	
		
	def _create_players(self, config):
		
		return tlist([
			Player('Player1', symbol=config.basics.characters.p1, val=1), # X
			Player('Player2', symbol=config.basics.characters.p2, val=-1), # O
		])
	
	def _set_phase_stack(self, config):
		
		return tlist([self._get_phase('turn')()])
	
	def _init_game(self, config):
		
		side = config.basics.side_length
		
		self.state.map = np.zeros((side, side), dtype=int)
		
		self.state.turn_counter = 0
		
	def _end_game(self):
		
		val = self.state.winner
		
		for p in self.players:
			if p.val == val:
				return tdict(winner=p.name)
			
		raise Exception('No player with val: {}'.format(val))