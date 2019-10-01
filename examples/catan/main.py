import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, containerify
from gsm.common.elements import Card

from .phases import SetupPhase, MainPhase, TradePhase
from .objects import Hex, Board, DevCard

MY_PATH = os.path.dirname(os.path.abspath(__file__))

class Catan(gsm.GameController):
	
	def __init__(self, debug=False, player_names=None,
	             num_players=3, colors=['White', 'Red', 'Blue', 'Orange'],
	             shuffle_order=False):
		
		# create player manager
		manager = gsm.GameManager(open={'num_res', 'num_dev', 'color', 'reserve', 'ports'},
		                          hidden={'vps'})
		
		super().__init__(debug=debug,
		                 manager=manager,
		                 # settings
		                 shuffle_order=shuffle_order)
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('dev', os.path.join(MY_PATH,'config/dev_cards.yaml'))
		self.register_config('map', os.path.join(MY_PATH,'config/map.yaml'))
		
		# register players
		if player_names is None:
			player_names = colors
		for i, name, color in zip(range(num_players), player_names, colors):
			self.register_player(name, num_res=0, num_dev=0, color=color)
		
		# register game object types
		self.register_obj_type(obj_cls=Board)
		self.register_obj_type(obj_cls=Hex, open={'resource', 'number'})
		self.register_obj_type(obj_cls=DevCard,
		                       req={'name', 'desc'},)
		self.register_obj_type(name='Robber', open={'loc'})
		self.register_obj_type(name='Road', open={'loc', 'owner'})
		self.register_obj_type(name='Settlement', open={'loc', 'owner'})
		self.register_obj_type(name='City', open={'loc', 'owner'})
		
		# register possible phases
		self.register_phase(name='setup', cls=SetupPhase)
		self.register_phase(name='main', cls=MainPhase)
		self.register_phase(name='trade', cls=TradePhase)
	
	def _pre_setup(self, config):
		pass
	
	def _set_phase_stack(self, config):
		return tlist([self.create_phase('main'), self.create_phase('setup')])
	
	def _init_game(self, config):
		
		# update player props
		for player in self.players.values():
			player.reserve = tdict(config.rules.building_limits)
			
		self.state.costs = config.rules.building_costs
		
		bank = tdict()
		for res in ['wood', 'brick', 'sheep', 'ore', 'wheat']:
			bank[res] = config.rules.num_res
		self.state.bank = bank
		
		self.state.rewards = config.rules.victory_points
		self.state.reqs = config.rules.reqs
		self.state.victory_condition = config.rules.victory_condition
		
		# init map
		# TODO
		side = config.basic.side_length
		
		self.state.map = gsm.Array(np.zeros((side, side), dtype=int))
		
		self.state.turn_counter = -1
		self.state.player_order = tlist(self.players.values())
		if 'shuffle_order' in config.settings:
			self.RNG.shuffle(self.state.player_order)
		
		
	def _end_game(self):
		
		val = self.state.winner
		
		if val is None:
			return tdict(winner=None)
		
		for p in self.players.values():
			if p.val == val:
				return tdict(winner=p.name)
			
		raise Exception('No player with val: {}'.format(val))