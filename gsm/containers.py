
import sys, os, time
import random
from collections import OrderedDict
from structures import TransactionableObject


_global_id = 0

_primitives = (str, int, float, bool)

class UnknownObject(Exception):
	pass

class Container(TransactionableObject):
	def __init__(self, iterations=None, tracker=None):
		self.data = OrderedDict()
		if iterations is None:
			iterations = lambda x: x.values()
		super().__init__(self, iterations=iterations)
	
	def __setattr__(self, key, item):
		if isinstance(item, (Container,) + _primitives):
			super().__setattr__(key, item)
		else:
			raise UnknownObject(key, item)
	
	def __setstate__(self, state):
		for key, value in state.items():
			if isinstance(value, dict) and '_type' in value:
				info = value
				value = eval(info['_type'] + '()')
				del info['_type']
				value.__setstate__(info)
			self.__dict__[key] = value
	
	def __getstate__(self):
		state = {}
		for key, value in self.__dict__.items():
			if isinstance(value, Container):
				info = value.__getstate__()
				info['_type'] = str(type(value).__name__)
			else:
				state[key] = value
		return state
	
	def copy(self):
		copy = type(self)()
		copy.__setstate__(self.__getstate__())
		return copy


class GameState(Container):
	pass

class GameObject(Container):
	
	def __init__(self, name=None, obj_type=None, **kwargs):
		super().__init__()
		self.name = name
		self.obj_type = obj_type
		self.__dict__.update(kwargs)
		
		global _global_id
		self._id = _global_id
		_global_id += 1
	
	def __repr__(self):
		return 'GameObject({})'.format(', '.join(['{}={}'.format(k, type(v).__name__ if isinstance(v,Container) else v)
		                                          for k,v in self.__dict__.items()]))
	
	def __str__(self):
		return self.name



