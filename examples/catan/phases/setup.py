import numpy as np
import gsm
from gsm import GamePhase, GameActions, PhaseComplete, GameOver
from gsm import tset, tdict, tlist


class SetupPhase(GamePhase):
	
	def __init__(self):
		super().__init__()
		self.available = None
	
	def execute(self, C, player=None, action=None):
		
		if self.available is None:
			self.available = tset(C.state.world.corners)
		
		if action is not None:
			
			turns = C.state.turns
			
			loc, = action
			
			if loc.obj_type == 'Edge':
				road = C.table.create('Road', loc=loc, owner=player.name)
				loc.color = player.color
				loc.player = player.name
				loc.building = 'road'
				player.buildings.road.add(road)
				
				if turns.counter == len(C.players)-1:
					turns.delta = -1
					turns.counter += 1
				turns.counter += turns.delta
				if turns.counter < 0:
					raise PhaseComplete
				
			elif loc.obj_type == 'Corner':
				settlement = C.table.create('Settlement', loc=loc, owner=player.name)
				loc.color = player.color
				loc.player = player.name
				loc.building = 'settlement'
				player.buildings.settlement.add(settlement)
				player.vps += 1
				
				self.settled = settlement
				
				for e in loc.edges:
					if e is not None:
						for c in e.corners:
							self.available.discard(c)
							
				if turns.delta < 0:
					
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
					
					
				
			C.log.writef('counter: {}', turns.counter, debug=True)
			turns.settle ^= True
				
		
	def encode(self, C):
		
		turns = C.state.turns
		player = turns.order[max(turns.counter,len(C.players)-1)]
		
		out = GameActions()
		
		out.begin()
		if turns.settle:
			loc_name = 'Settlement'
			out.write('Available Locations')
			out.add((self.available,))
		
		else:
			loc_name = 'Road'
			out.write('Available Edges')
			out.add((tset(e for e in self.settled.edges if 'building' not in e),))
		
		out.commit()
		out.status.writef('Choose a location to place a {}', loc_name)
		
		return tdict({player.name:out})