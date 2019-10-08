
from ... import tdict, tlist, tset, tdeque
from ... import GameObject, SafeGenerator



class Card(GameObject):
	
	def __init__(self, deck, **info):
		super().__init__(**info)
		
		self._deck = deck
	
	def discard(self):
		self._deck.discard(self)


class Deck(SafeGenerator):
	
	def __init__(self, cards, seed, default, top_face_up=None,
	             **info):
		super().__init__(seed=seed, objs=tdeque(cards), default=default, **info)
		
		self._top_face_up = top_face_up
		self._in_play = tdict()
		self._kwargs = tdict()
		
		self.shuffle()
		
		self._peek()
		
	def __len__(self):
		return len(self._objs)
	
	def _get(self, n=1):
		objs = tlist()
		for _ in range(n):
			obj = self._objs.popleft()
			obj.update(self._kwargs)
			objs.append(obj)
			
		self._peek()
		
		return objs
		
	def _add(self, *objs):
		clean = []
		for obj in objs:
			if 'visible' in obj:
				del obj.visible
			clean.append(obj)
		self._objs.extend(clean)
		self._peek()
	
	def _peek(self):
		if self._top_face_up is not None:
			self.next = tlist(self._objs[:self._top_face_up])
	
	def shuffle(self):
		self._rng.shuffle(self._objs)
		self._peek()
	
	def draw(self, n=None, player=None):
		
		if player is not None:
			self._kwargs = {'visible': tset([player.name])}
		
		cards = self.get(n)
		self._in_play.update({c._id:c for c in cards})
		
		self._kwargs = {}
		
		return cards
	
	def discard(self, *cards):
		
		for c in cards:
			del self._in_play[c._id]
			
		self.extend(cards)

	def retrieve_all(self):
		self.discard(*self._in_play.values())
