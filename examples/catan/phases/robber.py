import numpy as np
from gsm import GamePhase, GameActions, GameOver
from gsm import tset, tdict, tlist


class RobberPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if 'loc' not in self:
			C.log.writef('{} may move the robber.', player)
		
		else:
			pass
	
	def encode(self, C):
		
		raise NotImplementedError
		
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
		
		return tdict({player.name: out})


