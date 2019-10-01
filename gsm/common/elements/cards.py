
from ... import tdict, tlist, tset
from ... import GameObject, SafeGenerator



class Card(GameObject):
	
	def __init__(self, deck, **info):
		super().__init__(**info)
		
		self._hidden.deck = deck
	
	def discard(self):
		self._hidden.deck.discard(self)


class Deck(SafeGenerator):
	
	def __init__(self, cards, seed, default, top_face_up=None,
	             **info):
		super().__init__(seed=seed, objs=cards, default=default, **info)
		
		self._hidden.top_face_up = top_face_up
		self._hidden.in_play = tdict()
		
		self.shuffle()
		
		self._peek()
		
	def __len__(self):
		return len(self._hidden.objs)
	
	def _get(self, n=1):
		return tlist(self._hidden.objs.pop(0) for _ in range(n))
		
	def _add(self, *objs):
		self._hidden.objs.extend(objs)
	
	
	def _peek(self):
		if self._hidden.top_face_up is not None:
			self.next = tlist(self._hidden.objs[:self._hidden.top_face_up])
	
	def shuffle(self):
		self._hidden.rng.shuffle(self._hidden.objs)
		self._peek()
	
	def draw(self, n=None):
		
		cards = self.get(n)
		self._hidden.in_play.update({c._id:c for c in cards})
		
		self._peek()
		
		return cards
	
	def discard(self, *cards):
		
		for c in cards:
			del self._hidden.in_play[c._id]
			
		self.extend(cards)

	def retrieve_all(self):
		self.discard(*self._hidden.in_play.values())
