from collections import OrderedDict
from .common import condensed_str

# adict - dicts allowing access through attributes
class adict(OrderedDict):
	def __getattr__(self, key):
		return self.__getitem__(key)
	def __setattr__(self, key, value):
		if key == "__qualname__":
			super().__setattr__(key, value)
		return self.__setitem__(key, value)
	# def __missing__(self, key):
	#     return None
	def __iter__(self):
		return iter(self.keys())
	def __delattr__(self, item):
		return super().__delitem__(item)
	def __getstate__(self):
		return super().__getstate__()
	def copy(self):
		return adict(self.items())
	def __str__(self):
		items = []
		for k,v in self.items():
			items.append( '{}:{}'.format(str(k), condensed_str(v)) )
		return 'adict({})'.format(', '.join(items))
	def __repr__(self):
		return '{'+', '.join('{}:{}'.format(repr(k),repr(v)) for k,v in self.items())+'}'






