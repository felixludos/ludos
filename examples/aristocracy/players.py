from gsm import GamePlayer
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card, Deck
from gsm import util

class Aristocrat(GamePlayer, game='aristocracy', open={'hand', 'market', 'buildings', 'vps', 'hand_limit',
                                                       'money', 'order'}):
	
	def draw_cards(self, n=None, log=None):
		
		if n is None:
			n = self._draw_increment
		
		cards = self._deck.draw(n)
		
		if log is not None:
			log.writef('{} draws {}', self, util.format_quantity('card', len(cards)))
			log[self].writef('You draw: {}', ', '.join(cards))
		
		self.hand.update(cards)
	
	



