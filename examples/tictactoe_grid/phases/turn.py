
from gsm import GamePhase, GameActions, GameOver
from gsm import tset, tdict, tlist

class TurnPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if action is not None:
			C.state.turn_counter += 1
			
			# update map
			
			loc, = action
			
			assert loc._val == 0, 'this should not happen'
			
			loc._val = player.val
			loc.symbol = player.symbol
			loc.player = player
			
			# C.log.write(player, 'places at: {}, {}'.format(*action))
			C.log.writef('{} chooses {}', player, loc)
			
			# check for victory
			winner = C.state.board.check()
			if winner != 0:
				C.state.winner = winner
				raise GameOver
			
	
	def encode(self, C):
		
		player = C.state.player_order[C.state.turn_counter % len(C.players)]
		
		out = GameActions()
		
		free = C.state.board.get_free()
		
		if not len(free):
			C.state.winner = None
			raise GameOver
		
		out.begin()
		out.add(tset(free),)
		out.write('Available spots')
		out.commit()
		
		out.status.write('Place a tick into one of free spots')
		
		return tdict({player.name:out})


