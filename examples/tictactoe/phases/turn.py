
from gsm import GamePhase, GameActions


class TurnPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if action is not None:
			C.state.turn_counter += 1
			
			assert C.state.map[action] == 0, 'this should not happen'
			
			# update map
			
			C.state.map[action] = player.val
			
			row, col = action
			
			C.create_object('tick', row=row, col=col,
			                symbol=player.symbol, player=player.name)
			
			C.log.write(player, 'places at: {}, {}'.format(*action))
			
			# check for victory
			
			# check rows
			sums = C.state.map.sum(0)
			
	
	def encode(self, C):
		
		player = C.players[C.state.turn_counter % len(C.players)]
		
		out = GameActions()
		
		
		
		return tdict({player:out})
		
		pass


