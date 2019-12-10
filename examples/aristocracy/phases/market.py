
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
		
		out = GameActions('You have {} actions left'.format(len(self.market[self.player])))
		
		
		
		return tdict({self.player: out})

