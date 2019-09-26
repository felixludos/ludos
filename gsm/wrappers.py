
import random
import numpy as np
from wrapt import ObjectProxy

from .mixins import Savable, Transactionable
from .basic_containers import tdict, tset, tlist

# all wrapped objects must be able to be copied (shallow copy) using
# note: Transactionable objects cant be wrapped
class ObjectWrapper(Transactionable, Savable, ObjectProxy):
	# __slots__ = ['__wrapped__', '__wrapped_cls__']
	
	def __new__(cls, *args, **kwargs):
		obj = super().__new__(cls, _gen_id=False)
		
		# obj.__wrapped_cls__ = cls
		
		return obj
	
	def __init__(self, obj):
		# object.__setattr__(self, '__wrapped__', obj)
		super().__init__(obj)
		
		self._self__pack_id = Savable._Savable__gen_obj_id()
		
		self._self_shadow = None
		self._self_children = tset()
	
	def _getref(self):
		return self._self__pack_id
	
	def _pack_obj(self, obj):
		return self.__wrapped_cls__._pack_obj(obj)
	
	def _unpack_obj(self, data):
		return self.__wrapped_cls__._unpack_obj(data)
	
	# def __setattr__(self, name, value):
	# 	if name.startswith('_self_'):
	# 		print('setting', name, value)
	# 		object.__setattr__(self, name, value)
	#
	# 		print(hasattr(self, name))
	#
	# 	elif name == '__wrapped__' or name == '__wrapped_cls__':
	# 		object.__setattr__(self, name, value)
	# 		try:
	# 			object.__delattr__(self, '__qualname__')
	# 		except AttributeError:
	# 			pass
	# 		try:
	# 			object.__setattr__(self, '__qualname__', value.__qualname__)
	# 		except AttributeError:
	# 			pass
	#
	# 	elif name == '__qualname__':
	# 		setattr(self.__wrapped__, name, value)
	# 		object.__setattr__(self, name, value)
	#
	# 	elif hasattr(type(self), name):
	# 		object.__setattr__(self, name, value)
	#
	# 	else:
	# 		setattr(self.__wrapped__, name, value)
	
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
			
		self._self_shadow = self.copy()
		self._self_children.begin()
	
	def in_transaction(self):
		return self._self_shadow is not None
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._self_shadow = None
		self._self_children.commit()
		
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self.__wrapped__ = self._self_shadow
		self._self_shadow = None
		self._self_children.abort()
		
	def __repr__(self):
		return self.__wrapped__.__repr__()
	
	def __str__(self):
		return self.__wrapped__.__str__()
	
	# def __getattribute__(self, item):
	# 	if item in super().__getattribute__('_self_special_attrs'):
	# 		return
	
	def __setattr__(self, key, value):
		if isinstance(value, Transactionable) and not key == '_self_children':
			self._self_children.add(value)
		return super().__setattr__(key, value)
	
	def __delattr__(self, item):
		value = self.__getattr__(item)
		if isinstance(value, Transactionable):
			self._self_children.remove(value)
		return super().__delattr__(item)
	
	# @staticmethod
	# def _simple_method_wrapper(method, typ, wrapper):
	# 	def _exec(*args, **kwargs):
	# 		print('executing', method)
	# 		out = method(*args, **kwargs)
	# 		print(type(out), typ, wrapper)
	# 		if isinstance(out, typ):
	# 			return wrapper(out)
	# 		return out
	# 	return _exec
	
	
	@classmethod
	def __load__(self, data):
		obj = self.__build__(data)
		
		self.__init__(obj)
		
		# self.__wrapped__ = self.__build__(data)
	
	# must be overridden
	
	def __save__(self): # save everything from the internal state
		raise NotImplementedError
	
	def __build__(self, data): # recover wrapped object in correct state from data, return wrapped object
		raise NotImplementedError


class Array(ObjectWrapper): # wraps numpy arrays
	
	def __save__(self):
		pack = self.__wrapped_cls__._pack_obj
		
		data = {}
		
		data['dtype'] = pack(self.dtype.name)
		data['data'] = pack(self.tolist())
		
		return data
	
	def __build__(self, data):
		unpack = self.__wrapped_cls__._unpack_obj
		return np.array(unpack(data['data']), dtype=unpack(data['dtype']))
