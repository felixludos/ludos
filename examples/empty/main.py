import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, tdeque, tstack, containerify
from gsm.common.elements import Deck
from gsm.common.world import grid
from gsm.common import TurnPhaseStack

from .ops import build_catan_map, gain_res
from .phases import *
from .objects import Card, CustomObj

MY_PATH = os.path.dirname(os.path.abspath(__file__))

class EmptyGame(gsm.GameController):
	
	def __init__(self, player_names, debug=False, force_order=False):
		
		# create player manager
		manager = gsm.GameManager(open={'name', 'hand', 'buildings'})
		
		stack = TurnPhaseStack()
		
		log = gsm.GameLogger(indent_level=0)
		
		super().__init__(debug=debug,
		                 manager=manager,
		                 stack=stack,
		                 log=log,
		                 info_path=os.path.join(MY_PATH, 'info.yaml'),
		                 player_names=player_names,
		                 force_order=force_order,
		                 )
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		
		# register game object types
		self.register_obj_type(name='card', obj_cls=Card)
		self.register_obj_type(name='special', obj_cls=CustomObj)
		self.register_obj_type(name='normal',)
		
		# register possible phases
		self.register_phase(name='exm', cls=ExamplePhase)
		
	def _pre_setup(self, config, info=None):
		# register players
		assert 2 <= len(self.player_names) <= 4, 'Not the right number of players: {}'.format(len(self.player_names))
		for name in self.player_names:
			if name not in info.player_names:
				raise gsm.signals.InvalidPlayerError(name)
			self.register_player(name)
	
		# register buildings
		for name in config.rules.counts:
			self.register_obj_type(name=name, obj_cls=Building)
	
	def _set_phase_stack(self, config):
		self.stack.set_player_order(tlist(self.players))
		return tlist([self.create_phase('king')])
	
	def _init_game(self, config):
		
		self.state = config.rules
		
		
	def _end_game(self):
		
		out = tdict()
		
		vps = tdict({player.name:player.vps for player in self.players})
		out.vps = vps
		
		mx = max(vps.values())
		
		# TODO: break ties with money and hand card values
		
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
		
		# if code == 'devcard':
		# 	for player in self.players:
		# 		gain_res('wheat', self.state.bank, player, 1, log=self.log)
		# 		gain_res('ore', self.state.bank, player, 1, log=self.log)
		# 		gain_res('sheep', self.state.bank, player, 1, log=self.log)
		
		self.log.dindent()


gsm.register_game(Aristocracy, os.path.join(MY_PATH, 'info.yaml'))
