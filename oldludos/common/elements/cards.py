
from ... import gdict, glist, gset, gdeque
from ... import GameObject, SafeGenerator



class Card(GameObject):
	
	def __init__(self, deck, **info):
		super().__init__(**info)
		
		self._deck = deck
	
	def discard(self):
		self._deck.discard(self)
		
	def face_up(self):
		self.visible.update(self._table.players)
		
	def face_down(self, player=None):
		self.visible.clear()
		if player is not None:
			self.visible.add(player.name)


class Deck(SafeGenerator):
	
	def __init__(self, seed, default, cards=[], top_face_up=None,
	             **info):
		super().__init__(seed=seed, objs=gdeque(cards), default=default, **info)
		
		self._top_face_up = top_face_up
		self._in_play = gset()
		self._kwargs = tdict()
		
		self.shuffle()
		
		self._peek()
		
	def __len__(self):
		return len(self._objs)
	
	def _get(self, n=1):
		objs = glist()
		for _ in range(n):
			obj = self._objs.popleft()
			obj.deck = self
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
			self.next = glist(self._objs[:self._top_face_up])
	
	def shuffle(self):
		self._rng.shuffle(self._objs)
		self._peek()
	
	def draw(self, n=None, player=None):
		
		if player is not None:
			self._kwargs = {'visible': gset([player.name])}
		
		cards = self.get(n)
		if n is None:
			self._in_play.add(cards)
		else:
			self._in_play.update(cards)
		
		self._kwargs = {}
		
		return cards
	
	def discard(self, *cards):
		
		for c in cards:
			self._in_play.remove(c)
			
		self.extend(cards)

	def retrieve_all(self):
		self.discard(*self._in_play)
