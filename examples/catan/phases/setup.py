import numpy as np
from ludos import assert_
from ludos import GamePhase, GameActions, PhaseComplete, SwitchPhase
from ludos import gset, gdict, glist
from ludos.common import StagePhase, Entry_Stage, Stage, Decision, Decide, Switch

from ..ops import build, gain_res

class SetupPhase(StagePhase, name='setup', game='catan', start=True):
	
	def __init__(self, player_order, real_estate):
		super().__init__()
		self.available = gset(real_estate) # C.state.world.corners
		self.settled = None
		
		self.on_second = False
		self.player_order = player_order + player_order[::-1]
	
	@Entry_Stage('settlement')
	def set_settlement(self, C, player, action=None):
		
		if action is None:
			self.active = self.player_order.pop()
			raise Decide('settlement')
	
		loc, = action
		
		assert_(loc.obj_type == 'Corner', f'{loc} should be a corner')
		
		build(C, 'settlement', player, loc)
		self.settled = loc
		
		for e in loc.edges:
			if e is not None:
				for c in e.corners:
					self.available.discard(c)
		
		if self.on_second:
			res = glist()
			for f in loc.fields:
				if f is not None and f.res != 'desert':
					res.append(f.res)
			
			for r in res:
				gain_res(r, C.state.bank, player, 1)
			
			if len(res) == 3:
				s = '{}, {}, and {}'.format(*res)
			elif len(res) == 2:
				s = '{} and {}'.format(*res)
			elif len(res) == 1:
				s = '{}'.format(*res)
			else:
				s = 'no resources'
			C.log.writef('{} gains: {}', player, s)
			
		raise Switch('road')
		
	@Decision('settlement', ['loc-settlement'])
	def get_settlement(self, C):
		out = GameActions('Choose a location to place a settlement')
		with out('loc-settlement', 'Available Locations'):
			out.add(self.available)
		
		return gdict({self.active: out})
	
	@Stage('road')
	def set_road(self, C, player, action=None):
		
		if action is None:
			raise Decide('road')
		
		loc, = action
		
		assert_(loc.obj_type == 'Edge', f'{loc} should be an edge')
		
		build(C, 'road', player, loc)
		
		if len(self.player_order) == 0:
			raise SwitchPhase('main', stack=False)
		if len(self.player_order) == len(C.players):
			self.on_second = True
		
		raise Switch('settlement')
	
	@Decision('road', ['loc-road'])
	def get_road(self, C):
		out = GameActions('Choose a location to place a road')
		with out('loc-road', 'Available Locations'):
			out.add(gset(e for e in self.settled.edges
			             if e is not None and 'building' not in e), )
		
		return gdict({self.active: out})
		