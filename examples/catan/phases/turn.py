
import numpy as np
from gsm import GamePhase, GameActions, GameOver
from gsm import tset, tdict, tlist

class TurnPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if action is not None:
			C.state.turn_counter += 1
			
			assert C.state.map[action] == 0, 'this should not happen'
			
			# update map
			
			C.state.map[action] = player.val
			
			row, col = map(int, action)
			
			C.create_object('tick', row=row, col=col,
			                symbol=player.symbol, player=player.name)
			
			# C.log.write(player, 'places at: {}, {}'.format(*action))
			C.log.writef('{} places at: {}, {}', player, *action)
			
			# check for victory
			L = C.state.map.shape[0]
			
			# check rows
			sums = C.state.map.sum(0)
			
			if (sums == L).any():
				C.state.winner = 1
				raise GameOver
			elif (sums == -L).any():
				C.state.winner = -1
				raise GameOver
			
			# check cols
			sums = C.state.map.sum(1)
			
			if (sums == L).any():
				C.state.winner = 1
				raise GameOver
			elif (sums == -L).any():
				C.state.winner = -1
				raise GameOver
			
			# check diag
			diag = np.diag(C.state.map).sum()
			if diag == L:
				C.state.winner = 1
				raise GameOver
			elif diag == -L:
				C.state.winner = -1
				raise GameOver
			
			diag = np.diag(np.fliplr(C.state.map)).sum()
			if diag == L:
				C.state.winner = 1
				raise GameOver
			elif diag == -L:
				C.state.winner = -1
				raise GameOver
			
	
	def encode(self, C):
		
		player = C.state.player_order[C.state.turn_counter % len(C.players)]
		
		out = GameActions()
		
		L = C.state.map.shape[0]
		
		r, c = np.mgrid[0:L, 0:L]
		free = C.state.map == 0
		
		# check for draw
		if free.sum() == 0:
			C.state.winner = None
			raise GameOver
		
		out.begin()
		out.update(zip(r[free], c[free]))
		out.write('Coordinate options')
		out.commit()
		
		out.status.write('Place a tick into one of these coords (row, col)')
		
		return tdict({player.name:out})


