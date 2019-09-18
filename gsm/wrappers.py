
import numpy as np
from wrapt import ObjectProxy

from .mixins import Savable, Transactionable
from .basic_containers import tdict, tset, tlist

# all wrapped objects must be able to be copied (shallow copy) using
# note: Transactionable objects cant be wrapped
class ObjectWrapper(ObjectProxy, Transactionable, Savable):
	
	def __init__(self, obj):
		super().__init__(obj)
		
		self._self_shadow = None
		self._self_children = tset()
	
	def begin(self):
		if self.in_transaction():
			self.commit()
			
		self._self_shadow = self.copy()
		self._self_children.begin()
	
	def in_transaction(self):
		return self._self_shadow is not None
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._self_children.commit()
		self._self_shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._self_children.abort()
		self.__wrapped__ = self._self_shadow
		self._self_shadow = None
		
	def __repr__(self):
		return self.__wrapped__.__repr__()
	
	def __str__(self):
		return self.__wrapped__.__str__()
	
	def __setattr__(self, key, value):
		if isinstance(value, Transactionable) and not key == '_self_children':
			self._self_children.add(value)
		return super().__setattr__(key, value)
	
	def __delattr__(self, item):
		value = self.__getattr__(item)
		if isinstance(value, Transactionable):
			self._self_children.remove(value)
		return super().__delattr__(item)
	
	@staticmethod
	def _simple_method_wrapper(method, typ, wrapper):
		def _exec(*args, **kwargs):
			print('executing', method)
			out = method(*args, **kwargs)
			print(type(out), typ, wrapper)
			if isinstance(out, typ):
				return wrapper(out)
			return out
		return _exec
	
	
	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		
		obj = cls.__build(data)
		return cls(obj)
	
	# must be overridden
	
	def __save(self): # save everything from the internal state
		raise NotImplementedError
	
	@classmethod
	def __build(cls, data): # recover wrapped object in correct state from data, return wrapped object
		raise NotImplementedError


class Array(ObjectWrapper): # wraps numpy arrays
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['dtype'] = self.dtype
		data['data'] = self.tolist()
		
		return data
	
	@classmethod
	def __build(self, data):
		return np.array(data['data'], dtype=data['dtype'])



