import sys, os
import numpy as np
import ludos
from ludos import adict, tlist, tset

from ludos import GameController, GameActions, GameOver, GamePlayer
from ludos.common import world, TurnPhase
from ludos.common.world import Grid, Field
from ludos import SwitchPhase


##################
# region Controller
##################

class TicTacToe(GameController):
	
	def _init_game(self, C, config, settings):
		
		# update player props
		
		p1, p2 = C.players
		
		p1.symbol = config.basic.characters.p1
		p2.symbol = config.basic.characters.p2
		
		p1._val = -1
		p2._val = 1
		
		# init state
		
		side = config.basic.side_length
		
		grid = world.make_quadgrid(rows=side, cols=side, table=C.table,
		                           field_obj_type='Tick', grid_obj_type='Board')
		
		C.state.board = grid
		
	def _end_game(self, C):
		
		val = C.state.winner
		
		if val is None:
			C.log.writef('Game over! Draw game!')
			return adict(winner=None)
		
		for player in C.players:
			if player._val == val:
				C.log.writef('Game Over! {} wins!', player)
				return adict(winner=player.name)
			
		raise Exception('No player with val: {}'.format(val))


# endregion
##################
# region Phases
##################

class TicPhase(TurnPhase, game='ttt', name='tic', start=True):
	
	def execute(self, C, player=None, action=None):
		
		if action is not None:
			
			# update map
			
			loc, = action
			
			assert loc._val == 0, 'this should not happen'
			
			loc._val = player._val
			loc.symbol = player.symbol
			loc.player = player
			
			# C.log.write(player, 'places at: {}, {}'.format(*action))
			C.log.writef('{} chooses {}', player, loc)
			
			# check for victory
			winner = C.state.board.check()
			if winner != 0:
				C.state.winner = winner
				raise GameOver
			
			raise SwitchPhase('tic')
	
	def encode(self, C):
		
		out = GameActions('Place a tick into one of free spots')
		
		free = C.state.board.get_free()
		
		if not len(free):
			C.state.winner = None
			raise GameOver
		
		with out('tic', desc='Available spots'):
			out.add(tset(free))
		
		return adict({self.player: out})


# endregion
##################
# region Objects
##################

class Board(Grid, game='ttt'):
	
	def check(self):
		L = self.map.shape[0]
		
		# check rows
		sums = self.map.sum(0)
		
		if (sums == L).any():
			return 1
		elif (sums == -L).any():
			return -1
		
		# check cols
		sums = self.map.sum(1)
		
		if (sums == L).any():
			return 1
		elif (sums == -L).any():
			return -1
		
		# check diag
		diag = np.diag(self.map).sum()
		if diag == L:
			return 1
		elif diag == -L:
			return -1
		
		diag = np.diag(np.fliplr(self.map)).sum()
		if diag == L:
			return 1
		elif diag == -L:
			return -1
		
		return 0
	
	def get_free(self):
		free = self.map == 0
		return self.map[free]

class Tick(Field, game='ttt'):
	def __init__(self, **props):
		super().__init__(**props)
		
		self._val = 0
	
	def __eq__(self, other):
		try:
			return self._val == other._val
		except AttributeError:
			return self._val == other
	
	def __hash__(self):
		return super().__hash__()
	
	def __add__(self, other):
		try:
			return self._val + other._val
		except AttributeError:
			return self._val + other
	
	def __radd__(self, other):
		return self.__add__(other)
	
	def __str__(self):
		return '({},{})'.format(self.row, self.col)


# endregion
##################
# region Players
##################

class TTT_Player(GamePlayer, game='ttt', open={'symbol'}):
	pass


# endregion
##################

