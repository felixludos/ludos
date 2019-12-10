import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, tdeque, tstack, containerify
from gsm.common.elements import Deck
from gsm.common.world import grid
from gsm.common import TurnPhaseStack

from .ops import build_catan_map, gain_res
from .phases import *
from .objects import Card, DiscardPile, DrawPile, Building, Market

MY_PATH = os.path.dirname(os.path.abspath(__file__))



class Aristocracy(gsm.GameController):
	
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
		self.register_config('card', os.path.join(MY_PATH,'config/cards.yaml'))
		self.register_config('msgs', os.path.join(MY_PATH,'config/msgs.yaml'))
		
		# register game object types
		self.register_obj_type(name='card', obj_cls=Card)
		self.register_obj_type(name='discard_pile', obj_cls=DiscardPile)
		self.register_obj_type(name='draw_pile', obj_cls=DrawPile,)
		self.register_obj_type(name='market', obj_cls=Market)
		
		# register possible phases
		self.register_phase(name='king', cls=KingPhase)
		self.register_phase(name='queen', cls=QueenPhase)
		self.register_phase(name='jack', cls=JackPhase)
		
		self.register_phase(name='auction', cls=AuctionPhase)
		self.register_phase(name='ball', cls=BallPhase)
		self.register_phase(name='market', cls=MarketPhase)
		self.register_phase(name='tax', cls=TaxPhase)
		self.register_phase(name='claim', cls=ClaimPhase)
		
		
	def _pre_setup(self, config, info=None):
		# register players
		assert 2 <= len(self.player_names) <= 5, 'Not the right number of players: {}'.format(len(self.player_names))
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
		
		cards = tlist()
		
		num = config.rules.num_numbers
		for n, c in config.cards.items():
			if n in config.rules.num_royals:
				cards.extend([c]*config.rules.num_royals[n])
			else:
				cards.extend([c]*num)
		
		self.state.discard_pile = self.create_object('discard_pile', top_face_up=config.rules.discard_market,
		                                            seed=self.RNG.getrandbits(32), default='card')
		
		self.state.deck = self.create_object('draw_pile', discard_pile=self.state.discard_pile,
		                                    cards=cards, seed=self.RNG.getrandbits(32), default='card')
		self.state.deck.shuffle()
		
		self.state.market = self.create_object('market', neutral=tset(),
		                                       _log=self.log, _deck=self.state.deck)
		
		self.state.royal_phases = config.rules.royal_phases
		
		for i, player in enumerate(self.players):
			player.hand = tset(self.state.deck.draw(config.rules.hand_size.starting))
			player.buildings = tdict({bld:tlist() for bld in config.rules.counts})
			player.vps = 0
			player.hand_limit = config.rules.hand_size.max
			player.coins = 3
			player.order = i + 1
			if i == 0:
				self.state.herald = player
		
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
