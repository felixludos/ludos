import sys, os
import numpy as np
import ludos
from ludos import adict, tlist, tset, tdeque, tstack, containerify
from ludos.errors import InvalidPlayerError
from ludos.common.world import grid
from ludos.common import TurnPhaseStack

from .phases import MainPhase, RobberPhase, SetupPhase, TradePhase
from . import objects
from . import players

from .ops import build_catan_map, gain_res

MY_PATH = os.path.dirname(os.path.abspath(__file__))



class Catan(ludos.GameController):
	
	def _create_start_phase(self, C, config, settings, **kwargs):
		super()._create_start_phase(C, config, settings,
		                            player_order=tlist(C.players),
		                            real_estate=C.state.world.corners,
		                            **kwargs)
	
	def _init_game(self, C, config, settings):
		
		res_names = config.rules.res_names
		
		# update player props
		for player in C.players.values():
			player.reserve = adict(config.rules.building_limits)
			player.buildings = adict(road=tset(), settlement=tset(), city=tset())
			player.resources = adict({res:0 for res in res_names})
			player.num_res = 0
			player.devcards = tset()
			player.past_devcards = tset()
			player.vps = 0
			player.ports = tset()
			
		C.state.costs = config.rules.building_costs
		
		bank = adict()
		for res in res_names:
			bank[res] = config.rules.num_res
		C.state.bank = bank
		
		C.state.rewards = config.rules.victory_points
		C.state.production = config.rules.resource_pays
		C.state.reqs = config.rules.reqs
		C.state.victory_condition = config.rules.victory_condition
		C.state.hand_limit = config.rules.hand_limit
		# init map
		G = grid.make_hexgrid(config.map.map, table=C.table,
		                      enable_corners=True, enable_edges=True,
		                      field_obj_type='Field', grid_obj_type='Grid',
		                      )
		
		build_catan_map(G, config.map.fields, config.map.ports, config.rules.numbers, C.RNG)
		C.state.world = G
		
		# robber and numbers
		numbers = adict()
		loc = None
		for f in G.fields:
			if f.res == 'desert':
				loc = f
			else:
				if f.num not in numbers:
					numbers[f.num] = tset()
				numbers[f.num].add(f)
		assert loc is not None, 'couldnt find the desert'
		C.state.robber = C.table.create('robber', loc=loc)
		C.state.desert = loc
		C.state.numbers = numbers
		loc.robber = C.state.robber
		
		# setup dev card deck
		cards = tlist()
		
		for name, info in config.dev_cards.items():
			cards.extend([adict(name=name, desc=info.desc)]*info.num)
		
		C.state.dev_deck = C.table.create(obj_type='Deck', cards=cards,
		                                        seed=C.RNG.getrandbits(64),
		                                        default='Card')
		C.state.dev_deck.shuffle()
		
		C.state.bank_trading = config.rules.bank_trading
		C.state.msgs = config.msgs
		
		C.state.rolls = tstack()
		
	def _end_game(self, C):
		
		out = adict()
		
		vps = adict({player.name:player.vps for player in C.players})
		out.vps = vps
		
		mx = max(vps.values())
		
		winners = tlist()
		for name, V in vps.items():
			if V == mx:
				winners.append(name)
		
		if len(winners) == 1:
			out.winner = winners[0]
			return out
		out.winners = winners
		return out
	
	
	
	def cheat(self, code=None):
		
		self.log.writef('Cheat code activated: {}', code)
		self.log.iindent()
		
		if code == 'devcard':
			for player in self.manager:
				gain_res('wheat', self.state.bank, player, 1, log=self.log)
				gain_res('ore', self.state.bank, player, 1, log=self.log)
				gain_res('sheep', self.state.bank, player, 1, log=self.log)

		if code == 'road':
			for player in self.manager:
				gain_res('wood', self.state.bank, player, 1, log=self.log)
				gain_res('brick', self.state.bank, player, 1, log=self.log)
				
		if code == 'settlement':
			for player in self.manager:
				gain_res('wood', self.state.bank, player, 1, log=self.log)
				gain_res('brick', self.state.bank, player, 1, log=self.log)
				gain_res('wheat', self.state.bank, player, 1, log=self.log)
				gain_res('sheep', self.state.bank, player, 1, log=self.log)
				
		if code == 'city':
			for player in self.manager:
				gain_res('wheat', self.state.bank, player, 2, log=self.log)
				gain_res('ore', self.state.bank, player, 3, log=self.log)
		
		if code == 'next7' and 'rolls' in self.state:
			self.log.write('The next roll will be a 7')
			
			self.state.rolls.push(7)
		
		if code == 'gain8':
			self.log.write('White gains 8 resources')
			
			for res in self.manager['White'].resources.keys():
				gain_res(res, self.state.bank, self.manager['White'], 3, log=self.log)
		
		self.log.dindent()
