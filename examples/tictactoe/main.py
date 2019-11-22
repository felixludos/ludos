import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset
from gsm.common import world, TurnPhaseStack

from .phases import TicPhase
from .objects import Board, Tick

MY_PATH = os.path.dirname(os.path.abspath(__file__))

class TicTacToe(gsm.GameController):
	
	def __init__(self, player_names=['Player1', 'Player2'], debug=False):
		
		# create player manager
		manager = gsm.GameManager(open={'symbol'},
		                          hidden={'val'})
		
		super().__init__(debug=debug,
		                 manager=manager,
		                 stack=TurnPhaseStack(),
		                 info_path=os.path.join(MY_PATH, 'info.yaml'))
		
		# register config files
		self.register_config('basic', os.path.join(MY_PATH,'config/basics.yaml'))
		
		# register players
		assert len(player_names) == 2, 'Not the right number of players'
		self.register_player(player_names[0], val=1)
		self.register_player(player_names[1], val=-1)
		
		# register game object types
		self.register_obj_type(obj_cls=Tick)
		self.register_obj_type(obj_cls=Board)
		
		# register possible phases
		self.register_phase(name='tic', cls=TicPhase)
	
	def _set_phase_stack(self, config):
		self.stack.set_player_order(tlist(self.players))
		return tlist(['tic'])
	
	def _select_player(self):
		return next(iter(self.players))
	
	def _init_game(self, config):
		
		# update player props
		
		p1, p2 = self.players
		
		p1.symbol = config.basic.characters.p1
		p2.symbol = config.basic.characters.p2
		
		# init state
		
		side = config.basic.side_length
		
		grid = world.make_quadgrid(rows=side, cols=side, table=self.table,
		                           field_obj_type='Tick', grid_obj_type='Board')
		
		self.state.board = grid
		
	def _end_game(self):
		
		val = self.state.winner
		
		if val is None:
			self.log.writef('Game over! Draw game!')
			return tdict(winner=None)
		
		for player in self.players:
			if player.val == val:
				self.log.writef('Game Over! {} wins!', player)
				return tdict(winner=player.name)
			
		raise Exception('No player with val: {}'.format(val))
	
gsm.register_game(TicTacToe, os.path.join(MY_PATH, 'info.yaml'))
