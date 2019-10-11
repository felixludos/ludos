import numpy as np
from gsm import GamePhase, GameActions, PhaseComplete
from gsm import tset, tdict, tlist

from ..ops import gain_res, play_dev, steal_options

class RobberPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if 'knight' not in self:  # enforce hand limit
			if 'debt' in self: # debts have been tabulated
				if len(self.debt): # there are still outstanding debts
				
					res, = action
					
					self.choices[player].append(res)
					gain_res(res, C.state.bank, player, -1)
					C.log[player].writef('1 of your {} is stolen.', res)
					
					if self.debt[player] <= 1:
						del self.debt[player]
						C.log.writef('{} loses: {}', player, ', '.join(self.choices[player]))
						del self.choices[player]
				
			else:
			
				lim = C.state.hand_limit
				
				self.debt = tdict()
				self.choices = tdict()
				
				for player in C.players:
					if player.num_res > lim:
						self.debt[player] = player.num_res // 2
						self.choices[player] = tlist()
				
				if len(self.debt):
					return
		
		
		if 'loc' not in self:
			
			if action is None:
				return
			
			# if 'knight' not in self:
			# 	C.log.writef('{} may move the {}.', player, C.state.robber)
			
			loc, = action
			self.loc = loc
			
			prev = C.state.robber.loc
			del prev.robber
			loc.robber = C.state.robber
			C.state.robber.loc = loc
		
		else:
			
			opp, = action
			
			self.stolen = None
			if opp.num_res > 0:
				self.stolen = C.RNG.choices(*zip(*list(opp.resources.items())), k=1)[0]
				
				gain_res(self.stolen, C.state.bank, opp, -1)
				gain_res(self.stolen, C.state.bank, player, 1)
				
			if 'knight' in self:
				play_dev(player, self.knight)
				C.log.writef('{} plays {}', player, self.knight)
				C.log.writef('{} moves {} to {}', player, C.state.robber, self.loc)
				
			if self.stolen is not None:
				C.log.writef('{} steals a resource card from {}', player, opp)
				C.log[opp].writef('You lose a {}', self.stolen)
				C.log[player].writef('You gain a {}', self.stolen)
				
			raise PhaseComplete
		
	def encode(self, C):
		
		out = GameActions()
		
		if 'loc' not in self:
			pass
		
		
		if self.devcard.name == 'Knight':  # TODO: move to robber phase
			with out:
				if self.card_info is None:
					options = tset(f for f in C.state.world.fields if 'robber' not in f)
					out.add(options)
					out.add('cancel')
					out.set_status('Choose where to move the knight.')
				else:
					# identify players in loc
					opps = tset(c.building.player for c in self.card_info.corners
					            if 'building' in c and c.building.player != self.player)
					out.add(opps)
					out.add('cancel')
					out.set_status('Choose what player to steal from.')
		
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


