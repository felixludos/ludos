import numpy as np
import gsm
from gsm import GamePhase, GameActions, PhaseComplete
from gsm import tset, tdict, tlist

from ..ops import build

class SetupPhase(GamePhase):
	
	def __init__(self, player_order):
		super().__init__()
		self.available = None
		
		self.settled = None
		self.on_second = False
		self.player_order = player_order + player_order[::-1]
	
	def execute(self, C, player=None, action=None):
		
		if self.available is None:
			self.available = tset(C.state.world.corners)
			
		if action is not None:
			
			loc, = action
			
			if loc.obj_type == 'Edge':
				build(C, 'road', player, loc)
				self.settled = None
				
				self.player_order.pop()
				if len(self.player_order) == 0:
					C.stack.push('main')
					raise PhaseComplete()
				if len(self.player_order) == len(C.players):
					self.on_second = True
				
			elif loc.obj_type == 'Corner':

				build(C, 'settlement', player, loc)
				self.settled = loc
				
				for e in loc.edges:
					if e is not None:
						for c in e.corners:
							self.available.discard(c)
							
				if self.on_second:
					res = tlist()
					for f in loc.fields:
						if f is not None and f.res != 'desert':
							res.append(f.res)
					
					for r in res:
						C.state.bank[r] -= 1
						player.resources[r] += 1
					
					if len(res) == 3:
						s = '{}, {}, and {}'.format(*res)
					elif len(res) == 2:
						s = '{} and {}'.format(*res)
					elif len(res) == 1:
						s = '{}'.format(*res)
					else:
						s = 'no resources'
					C.log.writef('{} gains: {}', player, s)
				
		
	def encode(self, C):
		
		player = self.player_order[-1]
		
		out = GameActions()
		
		with out('loc', 'Available Locations'):
			if self.settled is None:
				loc_name = 'settlement'
				out.add(self.available,)
			else:
				loc_name = 'road'
				out.add(tset(e for e in self.settled.edges
				              if e is not None and 'building' not in e),)
			
		out.set_status('Choose a location to place a {}'.format(loc_name))
		
		return tdict({player.name:out})