
import sys, os, time
import random
from itertools import chain
import numpy as np
from collections import OrderedDict
from .signals import LoadInitFailureError
from .mixins import Transactionable, Savable

class Container(Transactionable, Savable):
	pass

def containerify(obj, obj_tbl=None):
	if isinstance(obj, list):
		return tlist([containerify(o) for o in obj])
	if isinstance(obj, dict):
		if '_set' in obj and len(obj) == 1:
			return tset([containerify(o) for o in obj['set']])
		if '_tuple' in obj and len(obj) == 1:
			return tuple(containerify(o) for o in obj['tuple'])
		if '_ndarray' in obj and '_dtype' in obj:
			return np.array(obj['_ndarray'], dtype=obj['_dtype'])
		return tdict({containerify(k):containerify(v) for k,v in obj.items()})
	return obj

class tdict(Container, OrderedDict): # keys must be primitives, values can be primitives or Savable instances/subclasses
	
	def __init__(self, *args, **kwargs):
		super().__init__()
		self.__dict__['_data'] = OrderedDict(*args, **kwargs)
		self.__dict__['_shadow'] = None
		
	def in_transaction(self):
		return self._shadow is not None
		
	def begin(self):
		if self.in_transaction():
			self.commit() # partial transactions are committed
			
		self._shadow = self._data
		
		for child in self.values(): # if keys could be Transactionable instances: chain(self.keys(), self.values())
			if isinstance(child, Transactionable):
				child.begin()
		
		self._data = self._data.copy()
		
	def commit(self):
		if not self.in_transaction():
			return
		
		for child in self.values(): # if keys could be Transactionable instances: chain(self.keys(), self.values())
			if isinstance(child, Transactionable):
				child.commit()
				
		self._shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
		for child in self.values(): # if keys could be Transactionable instances: chain(self.keys(), self.values())
			if isinstance(child, Transactionable):
				child.abort()
		
		self._data = self._shadow
		
	def update(self, other):
		self._data.update(other)
	def fromkeys(self, keys, value=None):
		self._data.fromkeys(keys, value)
		
	def clear(self):
		self._data.clear()
	
	def copy(self):
		copy = type(self)()
		copy._data = self._data.copy()
		if self._shadow is not None:
			copy._shadow = self._shadow.copy()
		return copy
	
	def __len__(self):
		return len(self._data)
	
	def __hash__(self):
		return id(self)
	def __eq__(self, other):
		return id(self) == id(other)
	
	def __contains__(self, item):
		return self._data.__contains__(item)
	def __reversed__(self):
		return self._data.__reversed__()
	
	def __iter__(self):
		return iter(self._data)
	def keys(self):
		return self._data.keys()
	def values(self):
		return self._data.values()
	def items(self):
		return self._data.items()
	
	def pop(self, key):
		return self._data.pop(key)
	def popitem(self):
		return self._data.popitem()
	def move_to_end(self, key, last=True):
		self._data.move_to_end(key, last)
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		data['_pairs'] = {key:pack(value)
		                  for key, value in self.items()}
		
		data['_order'] = list(iter(self))
		
		if self.in_transaction(): # TODO: maybe write warning about saving in the middle of a transaction
			data['_shadow_pairs'] = {key:pack(value)
		                  for key, value in self._shadow.items()}
			
			data['_shadow_order'] = list(iter(self._shadow))
		
		return data
	
	@classmethod
	def __load(cls, data):
		self = cls()
		unpack = cls.__unpack
		
		# TODO: write warning about overwriting state - which can't be aborted
		# if self.in_transaction():
		# 	pass
		
		self._data.clear()
		for key in data['_order']:
			self._data[key] = unpack(data['_pairs'][key])
			
		if '_shadow_pairs' in data: # TODO: maybe write warning about loading into a partially completed transaction
			self._shadow = OrderedDict()
			for key in data['_shadow_order']:
				self._shadow[key] = unpack(data['_shadow_pairs'][key])
			
		return self
	
	def get(self, k):
		return self._data.get(k)
	def setdefault(self, key, default=None):
		self._data.setdefault(key, default)
	
	def __getitem__(self, item):
		return self._data[item]
	def __setitem__(self, key, value): # TODO: write warning if key is not a primitive, subclass of Savable, or instance of Savable
		self._data[key] = value
	def __delitem__(self, key):
		del self._data[key]
		
	def __getattr__(self, item):
		if item in self.__dict__:
			return super().__getattribute__(item)
		return self.__getitem__(item)
	def __setattr__(self, key, value):
		if key in self.__dict__:
			return super().__setattr__(key, value)
		return self.__setitem__(key, value)
	def __delattr__(self, item):
		if item in self.__dict__:
			# raise Exception('{} cannot be deleted'.format(item))
			return super().__delattr__(item)
		return self.__getitem__(item)
	
	def __str__(self):
		return 'tdict({})'.format(', '.join([str(key) for key in iter(self)]))
	def __repr__(self):
		return 'tdict({})'.format(', '.join(['{}:{}'.format(repr(key), repr(value)) for key, value in self.items()]))
	
class tlist(Container, list):

	def __init__(self, *args, **kwargs):
		super().__init__()
		self._data = list(*args, **kwargs)
		self._shadow = None
	
	def in_transaction(self):
		return self._shadow is not None
	
	def begin(self):
		if self.in_transaction():
			self.commit() # partial transactions are committed
		
		self._shadow = self._data
		
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.begin()
		
		self._data = self._data.copy()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.commit()
		
		self._shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.abort()
		
		self._data = self._shadow
	
	def copy(self):
		copy = type(self)()
		copy._data = self._data.copy()
		if self._shadow is not None:
			copy._shadow = self._shadow.copy()
		return copy
	
	def __save(self):
		pack = self.__class__.__pack
		state = {}
		state['_entries'] = [pack(elm) for elm in iter(self)]
		if self.in_transaction(): # TODO: maybe write warning about saving in the middle of a transaction
			state['_shadow'] = [pack(elm) for elm in self._shadow]
		return state
	
	@classmethod
	def __load(cls, state):
		
		self = cls()
		unpack = cls.__unpack
		
		# TODO: write warning about overwriting state - which can't be aborted
		# if self.in_transaction():
		# 	pass
		
		self._data.extend(unpack(elm) for elm in state['_entries'])
		if '_shadow' in state: # TODO: maybe write warning about loading into a partially completed transaction
			self._shadow = [unpack(elm) for elm in state['_shadow']]
			
		return self
	
	def __getitem__(self, item):
		return self._data[item]
	def __setitem__(self, key, value):
		self._data[key] = value
	def __delitem__(self, idx):
		del self._data[idx]
		
	def __hash__(self):
		return id(self)
	def __eq__(self, other):
		return id(self) == id(other)
		
	def count(self, object):
		return self._data.count(object)
	
	def append(self, item):
		return self._data.append(item)
	
	def __contains__(self, item):
		return self._data.__contains__(item)
	
	def extend(self, iterable):
		return self._data.extend(iterable)
		
	def insert(self, index, object):
		self._data.insert(index, object)
		
	def remove(self, value):
		self._data.remove(value)
		
	def __iter__(self):
		return iter(self._data)
	def __reversed__(self):
		return self._data.__reversed__()
	
	def reverse(self):
		self._data.reverse()
		
	def pop(self, index=None):
		if index is None:
			return self._data.pop()
		return self._data.pop(index)
		
	def __len__(self):
		return len(self._data)
		
	def clear(self):
		self._data.clear()
		
	def sort(self, key=None, reverse=False):
		self._data.sort(key, reverse)
		
	def index(self, object, start=None, stop=None):
		self._data.index(object, start, stop)
	
	def __mul__(self, other):
		return self._data.__mul__(other)
	def __rmul__(self, other):
		return self._data.__rmul__(other)
	def __add__(self, other):
		return self._data.__add__(other)
	def __iadd__(self, other):
		self._data.__iadd__(other)
	def __imul__(self, other):
		self._data.__imul__(other)
		
	def __repr__(self):
		return '[{}]'.format(', '.join(map(repr, self)))
	def __str__(self):
		return '[{}]'.format(', '.join(map(str, self)))
	
class tset(Container, set):
	
	def __init__(self, iterable=[]):
		super().__init__()
		self._data = OrderedDict()
		for x in iterable:
			self.add(x)
		self._shadow = None
	
	def in_transaction(self):
		return self._shadow is not None
	
	def begin(self):
		if self.in_transaction():
			self.commit() # partial transactions are committed
		
		self._shadow = self._data
		
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.begin()
		
		self._data = self._data.copy()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.commit()
		
		self._shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
		for child in iter(self):
			if isinstance(child, Transactionable):
				child.abort()
		
		self._data = self._shadow
	
	def copy(self):
		copy = type(self)()
		copy._data = self._data.copy()
		if self._shadow is not None:
			copy._shadow = self._shadow.copy()
		return copy
	
	def __save(self):
		pack = self.__class__.__pack
		state = {}
		state['_elements'] = [pack(elm) for elm in iter(self)]
		if self.in_transaction():
			state['_shadow'] = [pack(elm) for elm in self._shadow]
		return state
	
	@classmethod
	def __load(cls, data):
		self = cls()
		unpack = cls.__unpack
		
		# TODO: write warning about overwriting state - which can't be aborted
		# if self.in_transaction():
		# 	pass
		
		self._data.update(unpack(elm) for elm in data['_elements'])
		
		if '_shadow' in data: # TODO: maybe write warning about loading into a partially completed transaction
			self._shadow = OrderedDict()
			for elm in data['_shadow']:
				self._shadow[unpack(elm)] = None
		
		return self
	def __hash__(self):
		return id(self)
	def __eq__(self, other):
		return id(self) == id(other)
	
	def __and__(self, other):
		copy = self.copy()
		for x in self:
			if x in other:
				copy.add(x)
			else:
				copy.remove(x)
		return copy
	def __or__(self, other):
		copy = self.copy()
		copy.update(other)
		return copy
	def __xor__(self, other):
		copy = self.copy()
		for x in list(other):
			if x in other:
				copy.add(x)
			else:
				copy.remove(x)
		return copy
	def __sub__(self, other):
		copy = self.copy()
		for x in other:
			copy.discard(x)
		return copy
	
	def __rand__(self, other):
		return self & other
	def __ror__(self, other):
		return self | other
	def __rxor__(self, other):
		return self ^ other
	def __rsub__(self, other):
		copy = other.copy()
		for x in self:
			copy.discard(x)
		return copy
	
	def difference_update(self, other):
		self -= other
	def intersection_update(self, other):
		self &= other
	def union_update(self, other):
		self |= other
	def symmetric_difference_update(self, other):
		self ^= other
	
	def symmetric_difference(self, other):
		return self ^ other
	def union(self, other):
		return self | other
	def intersection(self, other):
		return self & other
	def difference(self, other):
		return self - other
	
	def issubset(self, other):
		for x in self:
			if x not in other:
				return False
		return True
	def issuperset(self, other):
		for x in other:
			if x not in self:
				return False
		return True
	def isdisjoint(self, other):
		return not self.issubset(other) and not self.issuperset(other)
		
	def __iand__(self, other):
		for x in list(self):
			if x not in other:
				self.remove(x)
	def __ior__(self, other):
		self.update(other)
	def __ixor__(self, other):
		for x in other:
			if x in self:
				self.remove(x)
			else:
				self.add(x)
	def __isub__(self, other):
		for x in other:
			if x in self:
				self.remove(x)
	
	def pop(self):
		return self._data.popitem()[0]
	
	def remove(self, item):
		del self._data[item]
		
	def discard(self, item):
		if item in self._data:
			self.remove(item)
	
	def __contains__(self, item):
		return self._data.__contains__(item)
	
	def __len__(self):
		return len(self._data)
	
	def __iter__(self):
		return iter(self._data)
	
	def clear(self):
		return self._data.clear()
	
	def update(self, other):
		for x in other:
			self.add(x)
	
	def add(self, item):
		self._data[item] = None
		
	def __repr__(self):
		return '{' + ', '.join([repr(x) for x in self]) + '}'

	def __str__(self):
		return '{' + ', '.join([str(x) for x in self]) + '}'

