import yaml
import numpy as np
import random
from .mixins import Named, Typed, Savable, Transactionable, _primitives
from .signals import UnknownElementError
from .basic_containers import tdict, tset, tlist


def jsonify(obj, tfm=None):
	if isinstance(obj, _primitives):
		return obj
	
	if isinstance(obj, dict):
		return {k: jsonify(v) for k, v in obj.items()}
	if isinstance(obj, list):
		return [jsonify(r) for r in obj]
	if isinstance(obj, tuple):
		return {'_tuple': [jsonify(r) for r in obj]}
	if isinstance(obj, set):
		return {'_set': [jsonify(r) for r in obj]}
	
	if tfm is not None:
		return tfm(obj, jsonify)
	
	raise UnknownElementError(obj)

def unjsonify(obj, tfm=None):
	if isinstance(obj, _primitives):
		return obj
	if isinstance(obj, list):
		return tlist([unjsonify(o) for o in obj])
	if isinstance(obj, dict):
		if len(obj) == 1 and '_tuple' in obj:
			return tuple(unjsonify(o) for o in obj['_tuple'])
		if len(obj) == 1 and '_set' in obj:
			return tset(unjsonify(o) for o in obj['_set'])
		
		return tdict({k:unjsonify(v) for k,v in obj.items()})
	
	if tfm is not None:
		return tfm(obj, unjsonify)
	
	raise UnknownElementError(obj)

class RandomGenerator(Savable, Transactionable, random.Random):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._shadow = None
	
	def copy(self):
		copy = RandomGenerator()
		copy.setstate(self.getstate())
		copy._shadow = self._shadow
		return copy
	
	def __save__(self):
		pack = self.__class__._pack_obj
		
		data = {}
		
		data['state'] = pack(self.getstate())
		if self._shadow is not None:
			data['_shadow'] = pack(self._shadow)
		
		return data
	
	def __load__(self, data):
		unpack = self.__class__._unpack_obj
		
		self._shadow = None
		
		x = unpack(data['state'])
		
		self.setstate(x)
		
		if '_shadow' in data:
			self._shadow = unpack(data['_shadow'])
		
	
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
		
		self._shadow = self.getstate()
	
	def in_transaction(self):
		return self._shadow is not None
	
	def commit(self):
		if not self.in_transaction():
			return
			
		self._shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
			
		self.setstate(self._shadow)
		self._shadow = None
	



















# class Empty(Savable, Transactionable):
#
# 	def __save(self):
# 		raise NotImplementedError
#
# 	@classmethod
# 	def __load__(self, data):
# 		raise NotImplementedError
#
# 	def begin(self):
# 		if self.in_transaction():
# 			self.commit()
#
# 		raise NotImplementedError
#
# 	def in_transaction(self):
# 		raise NotImplementedError
#
# 	def commit(self):
# 		if not self.in_transaction():
# 			return
#
# 		raise NotImplementedError
#
# 	def abort(self):
# 		if not self.in_transaction():
# 			return
#
# 		raise NotImplementedError

