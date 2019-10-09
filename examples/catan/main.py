import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, containerify
from gsm.common.elements import Card, Deck
from gsm.common.world import grid
from gsm.common import TurnPhaseStack

from .ops import build_catan_map
from .phases import *
from .objects import Hex, Board, DevCard

MY_PATH = os.path.dirname(os.path.abspath(__file__))

class Catan(gsm.GameController):
	
	def __init__(self, debug=False, player_names=None,
	             num_players=3, colors=['White', 'Red', 'Blue', 'Orange'],
	             shuffle_order=False):
		
		# create player manager
		manager = gsm.GameManager(open={'num_res', 'num_dev', 'color', 'reserve', 'ports'},
		                          hidden={'vps'})
		
		stack = TurnPhaseStack()
		
		log = gsm.GameLogger(indent_level=0)
		
		super().__init__(debug=debug,
		                 manager=manager,
		                 stack=stack,
		                 log=log,
		                 # settings
		                 shuffle_order=shuffle_order)
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('dev', os.path.join(MY_PATH,'config/dev_cards.yaml'))
		self.register_config('map', os.path.join(MY_PATH,'config/map.yaml'))
		self.register_config('msgs', os.path.join(MY_PATH, 'config/msgs.yaml'))
		
		# register players
		if player_names is None:
			player_names = colors
		for i, name, color in zip(range(num_players), player_names, colors):
			self.register_player(name, num_res=0, num_dev=0, color=color)
		
		# register game object types
		self.register_obj_type(name='board', obj_cls=Board)
		self.register_obj_type(name='hex', obj_cls=Hex)
		
		self.register_obj_type(name='devcard', obj_cls=DevCard,
		                       req={'name', 'desc'},)
		self.register_obj_type(name='devdeck', obj_cls=Deck)
		self.register_obj_type(name='Robber', open={'loc'})
		
		self.register_obj_type(name='road', open={'loc', 'player'})
		self.register_obj_type(name='settlement', open={'loc', 'player'})
		self.register_obj_type(name='city', open={'loc', 'player'})
		
		# register possible phases
		self.register_phase(name='setup', cls=SetupPhase)
		self.register_phase(name='main', cls=MainPhase)
		self.register_phase(name='trade', cls=TradePhase)
		self.register_phase(name='robber', cls=RobberPhase)
	
	def _set_phase_stack(self, config):
		self.stack.set_player_order(tlist(self.players))
		return tlist([self.create_phase('setup', player_order=tlist(self.players.values()))])
	
	def _init_game(self, config):
		
		res_names = config.rules.res_names
		
		# update player props
		for player in self.players.values():
			player.reserve = tdict(config.rules.building_limits)
			player.buildings = tdict(road=tset(), settlement=tset(), city=tset())
			player.resources = tdict({res:0 for res in res_names})
			player.devcards = tset()
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
		self.state.robber = self.table.create('Robber', loc=loc)
		self.state.desert = loc
		self.state.numbers = numbers
		
		# setup dev card deck
		cards = tlist()
		
		for name, info in config.dev.items():
			cards.extend([tdict(name=name, desc=info.desc)]*info.num)
		
		self.state.dev_deck = self.table.create(obj_type='devdeck', cards=cards,
		                                        seed=self.RNG.getrandbits(64),
		                                        default='devcard')
		self.state.dev_deck.shuffle()
		
		self.state.turns = tdict(
			order=tlist(self.players.values()),
			counter=0,
		)
		
		self.state.bank_trading = config.rules.bank_trading
		self.state.msgs = config.msgs
		
	def _end_game(self):
		
		out = tdict()
		
		vps = tdict({player.name:player.vps for player in self.players.values()})
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
