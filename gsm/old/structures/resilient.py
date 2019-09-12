
from collections import OrderedDict
import inspect

class Resilient(object):
	
	def meta(self):
		return inspect.getsource(type(self))
	
	def state_dict(self):
		raise NotImplementedError
	
	def load_state_dict(self, state):
		raise NotImplementedError
	
	def copy(self):
		raise NotImplementedError

class ResDict(Resilient):
	def __init__(self, *args, **kwargs):
		self._data = OrderedDict(*args, **kwargs)
		
	def __setattr__(self, key, item):
		if key == '_data':
			super().__setattr__(key, item)
		else:
			self._data[key] = item
		
	def __getattr__(self, item):
		if item == '_data':
			return super().__getattr__(item)
		return self._data[item]
	
	def __delattr__(self, item):
		assert item != '_data', 'cannot delete "_data"'
		del self._data[item]
		
	def __repr__(self):
		return repr(self._data)
		
	def __str__(self):
		return str(self._data)








