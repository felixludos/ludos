from ludos import GameObject, gdict, glist, gset
from ludos.mixins import Named
from ludos.common.world import grid
from ludos.common.elements import Card as CardBase
from ludos.common.elements import Deck

class Card(Named, CardBase, game='aristocracy', name='card'):
	
	def isroyal(self):
		return '_royal' in self
	
	def __str__(self):
		return self.value
	
class DiscardPile(Deck, game='aristocracy', name='discard_pile'):
	def __init__(self, seed, default, top_face_up):
		super().__init__(cards=tlist(), seed=seed, default=default,
		                 top_face_up=top_face_up)

class DrawPile(Deck, game='aristocracy', name='draw_pile'):
	def __init__(self, discard_pile, log, **props):
		super().__init__(_discard_pile=discard_pile, _log=log, **props)
	
	def draw(self, n=None, player=None):
		num = 1 if n is None else n
		if len(self) < num:
			self.refill()
		return super().draw(n=n, player=player)
	
	def discard(self, *cards):
		for c in cards:
			self._in_play.remove(c)
		
		self._discard_pile.extend(cards)
		
	def refill(self):
		self._log.write('Refilling {} with {}', self, self._discard_pile)
		
		self._objs.extend(self._discard_pile._objs)
		self._objs.clear()
		self.shuffle()
	
	

class Building(GameObject, game='aristocracy', name='building'): # TODO: handle game object super objects correctly
	def __init__(self, address, storage, owner, **props):
		super().__init__(harvest=None, owner=owner, storage=storage,
		                 address=address, intruders=glist(), # face up
		                 **props)

	def visit(self):
		raise NotImplementedError


class Market(GameObject, game='aristocracy', name='market'):
	
	def clear(self):
		self.neutral.clear()
	
	def update(self, cards):
		self.neutral.update(cards)
	
	def __iter__(self):
		return iter(self.neutral)
	
	def __len__(self):
		return len(self.neutral)
	
	def remove(self, *cards):
		for card in cards:
			self.neutral.discard(card)
			card.discard()
	
	def reset(self, num):
		
		cards = self._deck.draw(num)
		
		self._log.write('The neutral market is: {}'.format(', '.join(['{}'] * num)), *cards)
		
		self.clear()
		self.neutral.update(cards)
