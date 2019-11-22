import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, tdeque, tstack, containerify
from gsm.common.elements import Deck
from gsm.common.world import grid
from gsm.common import TurnPhaseStack

from .ops import build_catan_map, gain_res
from .phases import *
from .objects import Card, DiscardPile, DrawPile

MY_PATH = os.path.dirname(os.path.abspath(__file__))



class Aristocracy(gsm.GameController):
	
	def __init__(self, player_names, debug=False):
		
		# create player manager
		manager = gsm.GameManager(open={'name', 'hand'})
		
		stack = TurnPhaseStack()
		
		log = gsm.GameLogger(indent_level=0)
		
		super().__init__(debug=debug,
		                 manager=manager,
		                 stack=stack,
		                 log=log,
		                 info_path=os.path.join(MY_PATH, 'info.yaml'),)
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('card', os.path.join(MY_PATH,'config/cards.yaml'))
		self.register_config('msgs', os.path.join(MY_PATH,'config/msgs.yaml'))
		
		# register game object types
		self.register_obj_type(name='card', obj_cls=Card)
		self.register_obj_type(name='discard_pile', obj_cls=DiscardPile)
		self.register_obj_type(name='draw_pile', obj_cls=DrawPile,)
		
		# register possible phases
		self.register_phase(name='king', cls=KingPhase)
		self.register_phase(name='queen', cls=QueenPhase)
		self.register_phase(name='jack', cls=JackPhase)
		
		self.register_phase(name='auction', cls=AuctionPhase)
		self.register_phase(name='ball', cls=BallPhase)
		self.register_phase(name='market', cls=MarketPhase)
		self.register_phase(name='tax', cls=TaxPhase)
		
		
	def _pre_setup(self, config, info=None):
		# register players
		assert len(self.player_names) in {3,4}, 'Not the right number of players: {}'.format(self.player_names)
		for name in self.player_names:
			if name not in info.player_names:
				raise gsm.signals.InvalidPlayerError(name)
			self.register_player(name, num_res=0, color=name)
	
	def _set_phase_stack(self, config):
		self.stack.set_player_order(tlist(self.players))
		return tlist([self.create_phase('setup', player_order=tlist(self.players))])
	
	def _init_game(self, config):
		
		res_names = config.rules.res_names
		
		# update player props
		for player in self.players.values():
			player.reserve = tdict(config.rules.building_limits)
			player.buildings = tdict(road=tset(), settlement=tset(), city=tset())
			player.resources = tdict({res:0 for res in res_names})
			player.devcards = tset()
			player.past_devcards = tset()
			player.vps = 0
			player.ports = tset()
			
		self.state.costs = config.rules.building_costs
		
		bank = tdict()
		for res in res_names:
			bank[res] = config.rules.num_res
		self.state.bank = bank
		
		self.state.rewards = config.rules.victory_points
		self.state.production = config.rules.resource_pays
		self.state.reqs = config.rules.reqs
		self.state.victory_condition = config.rules.victory_condition
		self.state.hand_limit = config.rules.hand_limit
		# init map
		G = grid.make_hexgrid(config.map.map, table=self.table,
		                      enable_corners=True, enable_edges=True,
		                      
		                      field_obj_type='hex', grid_obj_type='board')
		
		build_catan_map(G, config.map.fields, config.map.ports, config.rules.numbers, self.RNG)
		self.state.world = G
		
		# robber and numbers
		numbers = tdict()
		loc = None
		for f in G.fields:
			if f.res == 'desert':
				loc = f
			else:
				if f.num not in numbers:
					numbers[f.num] = tset()
				numbers[f.num].add(f)
		assert loc is not None, 'couldnt find the desert'
		self.state.robber = self.table.create('robber', loc=loc)
		self.state.desert = loc
		self.state.numbers = numbers
		loc.robber = self.state.robber
		
		# setup dev card deck
		cards = tlist()
		
		for name, info in config.dev.items():
			cards.extend([tdict(name=name, desc=info.desc)]*info.num)
		
		self.state.dev_deck = self.table.create(obj_type='devdeck', cards=cards,
		                                        seed=self.RNG.getrandbits(64),
		                                        default='devcard')
		self.state.dev_deck.shuffle()
		
		self.state.bank_trading = config.rules.bank_trading
		self.state.msgs = config.msgs
		
		self.state.rolls = tstack()
		
	def _end_game(self):
		
		out = tdict()
		
		vps = tdict({player.name:player.vps for player in self.players})
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
			for player in self.players:
				gain_res('wheat', self.state.bank, player, 1, log=self.log)
				gain_res('ore', self.state.bank, player, 1, log=self.log)
				gain_res('sheep', self.state.bank, player, 1, log=self.log)

		if code == 'road':
			for player in self.players:
				gain_res('wood', self.state.bank, player, 1, log=self.log)
				gain_res('brick', self.state.bank, player, 1, log=self.log)
				
		if code == 'settlement':
			for player in self.players:
				gain_res('wood', self.state.bank, player, 1, log=self.log)
				gain_res('brick', self.state.bank, player, 1, log=self.log)
				gain_res('wheat', self.state.bank, player, 1, log=self.log)
				gain_res('sheep', self.state.bank, player, 1, log=self.log)
				
		if code == 'city':
			for player in self.players:
				gain_res('wheat', self.state.bank, player, 2, log=self.log)
				gain_res('ore', self.state.bank, player, 3, log=self.log)
		
		if code == 'next7' and 'rolls' in self.state:
			self.log.write('The next roll will be a 7')
			
			self.state.rolls.push(7)
		
		if code == 'gain8':
			self.log.write('White gains 8 resources')
			
			for res in self.players['White'].resources.keys():
				gain_res(res, self.state.bank, self.players['White'], 3, log=self.log)
		
		self.log.dindent()


gsm.register_game(Catan, os.path.join(MY_PATH, 'info.yaml'))
