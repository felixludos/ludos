import numpy as np
from gsm.common import StagePhase, Entry_Stage, Stage, Decision, Decide, Switch
from gsm import GamePhase, GameActions, PhaseComplete
from gsm import tset, tdict, tlist

from ..ops import gain_res, play_dev, steal_options

class RobberPhase(StagePhase, game='catan'):
	
	def __init__(self, player, **kwargs): # requires the player that should move the robber
		super().__init__(current_stage_policy='latest', player=player, **kwargs)
	
	@Entry_Stage('entry')
	def entry(self, C, player, action=None):
		
		if 'knight' not in self:
			raise Switch('debt')
		
		raise Switch('loc')
	
	@Decision('debt', ['robbed'])
	def decide_steal(self, C):
		outs = tdict()
		for player, topay in self.debt.items():
			outs[player] = GameActions('You are robbed, choose {} resources to discard.'.format(topay))
			with outs[player]('robbed', desc='Choose resource to discard'):
				outs[player].add(tset(res for res, num in player.resources.items() if num > 0))
		
		return outs
		
	@Stage('debt')
	def compute_debt(self, C, player, action=None):
		
		if 'debt' not in self:
			
			self.debt = tdict()
			self.choices = tdict()
			
			lim = C.state.hand_limit
			
			for player in C.players:
				if player.num_res > lim:
					self.debt[player] = player.num_res // 2
					self.choices[player] = tlist()
		
		elif action is not None:
			res, = action
			
			self.choices[player].append(res)
			gain_res(res, C.state.bank, player, -1)
			C.log[player].writef('1 of your {} is stolen.', res)
			self.debt[player] -= 1
			
			if self.debt[player] < 1:
				del self.debt[player]
				C.log.writef('{} loses: {}', player, ', '.join(self.choices[player]))
				del self.choices[player]
	
		if len(self.debt):
			raise Decide('debt')
			
		raise Switch('loc')
	
	@Decision('loc', ['loc', 'cancel'])
	def encode_locs(self, C):
		out = GameActions()
		
		with out('cancel', desc='Cancel playing knight'):
			out.add('cancel')
		
		with out('loc', desc='Choose where to move the robber'):
			options = tset(f for f in C.state.world.fields if 'robber' not in f)
			out.add(options)
			out.set_status('Choose where to move the robber.')
		
		return tdict({self.player: out})
	
	@Stage('loc')
	def find_loc(self, C, player, action=None):
		
		if action is None:
			raise Decide('loc')
		
		loc, = action
		self.loc = loc
		
		if loc == 'cancel':
			C.log[player].write('Cancel knight')
			raise PhaseComplete
		
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
			raise Switch('target')
		
		self.resolve(C)
	
	@Decision('target', ['targets', 'cancel'])
	def pick_target(self, C):
		out = GameActions()
		
		with out('target', desc='Choose which player to steal from'):
			if 'knight' in self:
				out.add('cancel')
			
			out.add(self.steal_options)
			out.set_status('Choose what player to steal from.')
		
		return tdict({self.player: out})
	
	@Stage('target')
	def set_target(self, C, player, action=None):
		
		if action is None:
			raise Decide('target')
		
		self.target, = action
		
		if self.target == 'cancel':
			C.log[player].write('Cancel knight')
			raise PhaseComplete
		
		self.resolve(C)
		
	def resolve(self, C): # not a stage since it doesn't lead to a decision
		
		self.stolen = None
		if self.target is not None:
			
			opp = self.target
			
			assert opp.num_res > 0, f'game error: opponent {opp} should have atleast one resource'
			
			if opp.num_res > 0:
				self.stolen = C.RNG.choice(sum([[r] * n for r, n in opp.resources.items()], []))
				
				gain_res(self.stolen, C.state.bank, opp, -1)
				gain_res(self.stolen, C.state.bank, self.player, 1)
		
		if 'knight' in self: # play knight
			play_dev(self.player, self.knight)
			C.log.writef('{} plays {}', self.player, self.knight)
			C.log.writef('{} moves {} to {}', self.player, C.state.robber, self.loc)
		
		if self.stolen is not None:
			C.log.writef('{} steals a resource card from {}', self.player, opp)
			C.log[opp].writef('You lose a {}', self.stolen)
			C.log[self.player].writef('You gain a {}', self.stolen)
		
		raise PhaseComplete
	

