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
		else:
			self.debt = tdict()
		
		
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
			
			if 'knight' not in self:
				C.log.writef('{} moves {} to {}', player, C.state.robber, self.loc)
		
			self.steal_options = steal_options(self.loc, player)
			if len(self.steal_options) == 0:
				self.target = None
			elif len(self.steal_options) == 1:
				self.target = self.steal_options.pop()
			else:
				return
		
		if 'target' in self:
			
			self.stolen = None
			if self.target is not None:
				
				opp = self.target
				
				if opp.num_res > 0:
					self.stolen = C.RNG.choice(sum([[r]*n for r,n in opp.resources.items()],[]))
					
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
		
		if 'debt' in self and len(self.debt):
			outs = tdict()
			for player, topay in self.debt.items():
				outs[player] = GameActions('You are robbed, choose {} resources to discard.'.format(topay))
				with outs[player]('robbed', desc='Choose resource to discard'):
					outs[player].add(tset(res for res, num in player.resources.items() if num > 0))
				
			return outs
		
		out = GameActions()
		
		if 'loc' not in self:
			with out('loc', desc='Choose where to move the robber'):
				
				if 'knight' in self:
					out.add('cancel')
				
				options = tset(f for f in C.state.world.fields if 'robber' not in f)
				out.add(options)
				out.set_status('Choose where to move the robber.')
				
		else:
			with out('target', desc='Choose which player to steal from'):
				
				if 'knight' in self:
					out.add('cancel')
				
				out.add(self.steal_options)
				out.set_status('Choose what player to steal from.')
		
		return tdict({self.player: out})


