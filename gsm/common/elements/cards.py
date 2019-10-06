
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
		self._hidden.kwargs = tdict()
		
		self.shuffle()
		
		self._peek()
		
	def __len__(self):
		return len(self._hidden.objs)
	
	def _get(self, n=1):
		objs = tlist()
		for _ in range(n):
			obj = self._hidden.objs.pop(0)
			obj.update(self._hidden.kwargs)
			objs.append(obj)
		return objs
		
	def _add(self, *objs):
		clean = []
		for obj in objs:
			if 'visible' in obj:
				del obj.visible
			clean.append(obj)
		self._hidden.objs.extend(clean)
	
	def _peek(self):
		if self._hidden.top_face_up is not None:
			self.next = tlist(self._hidden.objs[:self._hidden.top_face_up])
	
	def shuffle(self):
		self._hidden.rng.shuffle(self._hidden.objs)
		self._peek()
	
	def draw(self, n=None, player=None):
		
		if player is not None:
			self.kwargs = {'visible': tset([player.name])}
		
		cards = self.get(n)
		self._hidden.in_play.update({c._id:c for c in cards})
		
		self.kwargs = {}
		
		self._peek()
		
		return cards
	
	def discard(self, *cards):
		
		for c in cards:
			del self._hidden.in_play[c._id]
			
		self.extend(cards)

	def retrieve_all(self):
		self.discard(*self._hidden.in_play.values())
