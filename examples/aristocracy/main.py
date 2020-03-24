import sys, os
import numpy as np
import gsm
from gsm import tdict, tlist, tset, tdeque, tstack, containerify
from gsm import register_object
from gsm.common.elements import Deck
from gsm.common.world import grid
from gsm.common import TurnPhaseStack

from .phases import *
from .objects import Card, DiscardPile, DrawPile, Building, Market

MY_PATH = os.path.dirname(os.path.abspath(__file__))



class Aristocracy(gsm.GameController):
	
	def _init_game(self, C, config, settings):
		
		for name in config.rules.counts:
			register_object(game='aristocracy', name=name, cls=Building)
		
		KingPhase.neutral_num = config.neutral_market.king
		QueenPhase.neutral_num = config.neutral_market.queen
		JackPhase.neutral_num = config.neutral_market.jack
		
		cards = tlist()
		
		num = config.rules.num_numbers
		for n, c in config.cards.items():
			if n in config.rules.num_royals:
				cards.extend([c] * config.rules.num_royals[n])
			else:
				cards.extend([c] * num)
		
		C.state.discard_pile = C.create_object('discard_pile', top_face_up=config.rules.discard_market,
		                                             seed=C.RNG.getrandbits(32), default='card')
		
		C.state.deck = C.create_object('draw_pile', discard_pile=C.state.discard_pile,
		                                     cards=cards, seed=C.RNG.getrandbits(32), default='card')
		C.state.discard_pile._draw_pile = C.state.deck
		
		C.state.deck.shuffle()
		
		C.state.market = C.create_object('market', neutral=tset(),
		                                 _log=C.log, _deck=C.state.deck)
		
		
		for i, player in enumerate(C.players):
			player.hand = tset()
			player._draw_increment = config.rules.draw_cards
			player._deck = C.state.deck
			
			player.hand = tset()
			player.market = tset()
			
			player.buildings = tdict({bld:tset() for bld in config.rules.counts})
			
			player.vps = 0
			player.hand_limit = config.rules.max_hand_size
			player.money = config.rules.starting.coins
			player.order = i-1
			if i == 0:
				C.state.herald = player
	
	def _end_game(self, C):
		
		out = tdict()
		
		vps = tdict({player.name: player.vps for player in C.players})
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

