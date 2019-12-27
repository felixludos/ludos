
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import SwitchPhase, PhaseComplete

from gsm.common import TurnPhase

from ..ops import get_next_market

class MarketPhase(TurnPhase):
		
	def execute(self, C, player=None, action=None):
		
		if action is None:
			# self.neutrals = tset(C.deck.draw(C.config.rules.market_cards))
			self.num = len(self.sel[self.player])
			del self.sel[self.player]
			
			C.log.writef('{} may take {} action{}', self.player, self.num, 's' if self.num > 1 else '')
			
			return
		
		assert player == self.player, 'wrong player: {}'.format(player)
		
		obj, *other = action
		
		if 'trade' in self:
			
			pass
		
		else:
			self.num -= 1
			pass
		
		if self.num == 0:
			nxt = get_next_market(self.sel)
			if nxt is None:
				raise PhaseComplete
			else:
				raise SwitchPhase('market', stack=False, player=nxt, market=self.sel)
		
		raise NotImplementedError
	
	def encode(self, C):
		
		# complete trade
		if 'trade' in self:
			out = GameActions('Choose second card to exchange')
			
			with out('cancel', 'Cancel trade'):
				out.add('cancel')
				
			with out('trade', 'Second card to exchange'):
				cards = tset()
				if self.trade not in C.state.market:
					cards.update(C.state.market)
				for p in C.players:
					if self.trade not in p.market:
						cards.update(p.market)
				out.add(cards)
				
		else:
			
			out = GameActions('You have {} actions left'.format(len(self.market[self.player])))
			
			# trade
			
			
			# pickup
			
			# play royal
			
			# royal action
			
			# exchange building
		
		return tdict({self.player: out})

