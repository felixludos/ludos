import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset
from gsm.common import world, TurnPhaseStack

from .phases import TicPhase
from .objects import Board, Tick

MY_PATH = os.path.dirname(os.path.abspath(__file__))

class TicTacToe(gsm.GameController):
	
	def __init__(self, debug=False):
		
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
		self.register_player('Player1', val=1)
		self.register_player('Player2', val=-1)
		
		# register game object types
		self.register_obj_type(obj_cls=Tick)
		self.register_obj_type(obj_cls=Board)
		
		# register possible phases
		self.register_phase(name='tic', cls=TicPhase)
	
	def _set_phase_stack(self, config):
		self.stack.set_player_order(tlist(self.players))
		return tlist(['tic'])
	
	def _select_player(self):
		return self.players['Player1']
	
	def _init_game(self, config):
		
		# update player props
		
		self.players['Player1'].symbol = config.basic.characters.p1
		self.players['Player2'].symbol = config.basic.characters.p2
		
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
		
		for p in self.players.values():
			if p.val == val:
				self.log.writef('Game Over! {} wins!'.format(p))
				return tdict(winner=p.name)
			
		raise Exception('No player with val: {}'.format(val))
	
gsm.register_game(TicTacToe, os.path.join(MY_PATH, 'info.yaml'))
