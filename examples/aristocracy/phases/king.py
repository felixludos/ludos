
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase
from gsm.common import stages as stg
from gsm import util

from ..ops import satisfies_vic_req

from .royals import RoyalPhase

class KingPhase(RoyalPhase, game='aristocracy', name='king', start=True):
	@stg.Stage('pre')
	def pre_phase(self, C, player, action=None):
		
		# increment herald
		for p in C.players:
			p.order += 1
			p.order %= len(C.players)
			if p.order == 0:
				C.state.herald = p
				C.log.writef('{} becomes herald', p)
		
		# prep tax
		extra = tdict()
		for p in C.players:
			if len(p.hand) > p.hand_limit:
				extra[p] = len(p.hand) - p.hand_limit
		
		self.taxable = extra
		raise stg.Switch('tax')
		
	@stg.Stage('tax')
	def run_tax(self, C, player, action=None):
		
		if action is not None:
			
			card, = action
			
			player.hand.remove(card)
			card.discard()
			
			self.taxable[player] -= 1
			if self.taxable[player] == 0:
				del self.taxable[player]
			
		if len(self.taxable):
			raise stg.Decide('tax')
		raise stg.Switch('market', royal='king')
	
	@stg.Decision('tax', ['tax'])
	def decide_tax(self, C):
		outs = tdict()
		for p, num in self.taxable.items():
			out = GameActions('You have too many cards, you must discard {} due to tax'.format(
				util.format_quantity('card', num)))
			with out('tax', 'Discard card'):
				out.add(p.hand)
			outs[p] = out
		
		return outs
	
	@stg.Stage('post')
	def post_phase(self, C, player, action=None):
		
		if 'candidates' not in self:
			self.candidates = tlist(p for p in C.players
			                        if satisfies_vic_req(p, C.config.rules.victory_conditions))
		
		if len(self.candidates):
			raise stg.Switch('claim')
		raise SwitchPhase('queen')
		
	@stg.Stage('claim')
	def claim(self, C, player, action=None):
		
		if action is None:
			raise stg.Decide('claim')
		
		cmd, = action
		if cmd == 'yes':
			C.log.writef('{} claims victory', player)
			C.state.claim = player
			raise GameOver
		self.candidates.remove(player)

		if len(self.candidates):
			raise stg.Decide('claim')
		raise stg.Switch('post')
	
	@stg.Decision('claim', ['end'])
	def decide_claim(self, C):
		
		out = GameActions('You have fulfilled the requirements to claim victory.')
		
		with out('end', 'End the game?'):
			out.add(tset(['yes', 'no']))
		
		return tdict({p:out for p in self.candidates})

