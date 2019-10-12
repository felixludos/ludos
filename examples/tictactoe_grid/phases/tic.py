
from gsm import GamePhase, GameActions, GameOver
from gsm.common import TurnPhase
from gsm import SwitchPhase
from gsm import tset, tdict, tlist

class TicPhase(TurnPhase):
	
	def execute(self, C, player=None, action=None):
		
		if action is not None:
			
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
			
			raise SwitchPhase('tic', stack=False)
			
	
	def encode(self, C):
		
		out = GameActions('Place a tick into one of free spots')
		
		free = C.state.board.get_free()
		
		if not len(free):
			C.state.winner = None
			raise GameOver
		
		with out('tic', desc='Available spots'):
			out.add(tset(free))
		
		return tdict({self.player:out})


