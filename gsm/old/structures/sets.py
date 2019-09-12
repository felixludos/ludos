from itertools import product
from collections import OrderedDict
# comparable set

_set_ID = 0
class xset(set):
	def __init__(self, iterable=None):
		if iterable is not None:
			self.data = OrderedDict({e: None for e in iterable})
		else:
			self.data = OrderedDict()
		global _set_ID
		self._id = _set_ID
		_set_ID += 1
		
	def add(self, item):
		self.data[item] = None
	def update(self, items):
		self.data.update({e:None for e in items})
	def discard(self, item):
		if item in self.data:
			del self.data[item]
	def remove(self, item):
		del self.data[item]
	def __iter__(self):
		return iter(self.data)
	def __len__(self):
		return len(self.data)
	def __contains__(self, item):
		return item in self.data
	def pop(self):
		return self.data.popitem()[0]
	def clear(self):
		return self.data.clear()
		
	def copy(self): # Copies have new IDs (can't be compared to originals)
		return xset(iter(self))
	def __eq__(self, other):
		return self._id == other._id
	def __hash__(self):
		return self._id
	def __repr__(self):
		# return '[{}]'.format(self._id) + '{' + ', '.join(map(repr, iter(self))) + '}'
		return '{'+', '.join(map(repr,iter(self)))+'}'
	def __str__(self):
		return '{'+', '.join(map(repr,iter(self)))+'}'
	def intersection(self, *others):
		new = self.copy()
		for x, other in product(self, others):
			if x not in other:
				new.remove(x)
		return new
	def union(self, *others):
		new = self.copy()
		for other in others:
			for x in other:
				new.add(x)
		return new
	
	def __isub__(self, other):
		for x in other:
			self.discard(x)
		return self
	
	def __imul__(self, other):
		for x in self.copy():
			if x not in other:
				self.discard(x)
		return self
	
	def difference(self, *others):
		new = self.copy()
		for other in others:
			for x in other:
				new.discard(x)
		return new


class xset_wrapper(set):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		global _set_ID
		self._id = _set_ID
		_set_ID += 1
	
	def copy(self):  # Copies have new IDs (can't be compared to originals)
		return xset(iter(self))
	
	def __eq__(self, other):
		return self._id == other._id
	
	def __hash__(self):
		return self._id
	
	def __repr__(self):
		# return '[{}]'.format(self._id) + '{' + ', '.join(map(repr, iter(self))) + '}'
		return '{' + ', '.join(map(repr, iter(self))) + '}'
	
	def __str__(self):
		return '{' + ', '.join(map(repr, iter(self))) + '}'
	
	def intersection(self, *others):
		new = self.copy()
		for x, other in product(self, others):
			if x not in other:
				new.remove(x)
		return new
	
	def union(self, *others):
		new = self.copy()
		for other in others:
			for x in other:
				new.add(x)
		return new
	
	def __isub__(self, other):
		for x in other:
			self.discard(x)
		return self
	
	def __imul__(self, other):
		for x in self.copy():
			if x not in other:
				self.discard(x)
		return self
	
	def difference(self, *others):
		new = self.copy()
		for other in others:
			for x in other:
				new.discard(x)
		return new


