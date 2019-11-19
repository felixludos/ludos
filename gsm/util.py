import yaml
import numpy as np
import random
from humpack import tdict, tset, tlist

from .mixins import Named, Typed, Jsonable, Savable, Transactionable, _primitives
from .signals import UnknownElementError, InvalidKeyError


def jsonify(obj, tfm=None):
	if tfm is not None:
		try:
			return tfm(obj, jsonify)
		except UnknownElementError:
			pass
	
	if isinstance(obj, _primitives):
		return obj
	
	if isinstance(obj, Jsonable):
		return obj.jsonify()
	if isinstance(obj, dict):
		out = {}
		for k, v in obj.items():
			if not isinstance(k, str):
				raise InvalidKeyError(k)
			out[k] = jsonify(v, tfm=tfm)
		return out
	if isinstance(obj, list):
		return [jsonify(r, tfm=tfm) for r in obj]
	if isinstance(obj, tuple):
		return {'_tuple': [jsonify(r, tfm=tfm) for r in obj]}
	if isinstance(obj, set):
		return {'_set': [jsonify(r, tfm=tfm) for r in obj]}
	if isinstance(obj, np.ndarray):
		return {'_ndarray': jsonify(obj.tolist(), tfm=tfm), '_dtype': obj.dtype.name}
	
	raise UnknownElementError(obj)


def unjsonify(obj, tfm=None):
	if tfm is not None:
		try:
			return tfm(obj, unjsonify)
		except UnknownElementError:
			pass
	if isinstance(obj, _primitives):
		return obj
	if isinstance(obj, list):
		return tlist([unjsonify(o, tfm=tfm) for o in obj])
	if isinstance(obj, dict):
		if len(obj) == 1 and '_tuple' in obj:
			return tuple(unjsonify(o, tfm=tfm) for o in obj['_tuple'])
		if len(obj) == 1 and '_set' in obj:
			return tset(unjsonify(o, tfm=tfm) for o in obj['_set'])
		if len(obj) == 2 and '_ndarray' in obj and '_dtype' in obj:
			return np.array(unjsonify(obj['_ndarray'], tfm=tfm), dtype=obj['_dtype'])
		return tdict({k: unjsonify(v, tfm=tfm) for k, v in obj.items()})
	
	raise UnknownElementError(obj)

def obj_unjsonify(obj, table=None):
	obj = unjsonify(obj)
	if table is not None:
		obj_cross_ref(obj, table)
	return obj
	
def _fmt_obj(obj, tables):
	if isinstance(obj, dict) and len(obj):
		k, v = next(iter(obj.items()))
		if k in tables and len(obj) == 1:
			return tables[k][v]
	obj_cross_ref(obj, tables)
	return obj
def obj_cross_ref(obj, tables):
	if isinstance(obj, dict):
		for k, v in obj.items():
			if isinstance(v, tuple):
				obj[k] = (_fmt_obj(o, tables) for o in v)
			elif isinstance(v, list):
				for i in range(len(v)):
					v[i] = _fmt_obj(v[i],tables)
			elif isinstance(v, set):
				cpy = v.copy()
				v.clear()
				for x in cpy:
					v.add(_fmt_obj(x, tables))
			else:
				obj[k] = _fmt_obj(v, tables)


class RandomGenerator(Savable, Transactionable, random.Random):
	
	def __init__(self, seed=None):
		super().__init__()
		self._shadow = None
		if seed is not None:
			self.seed(seed)
	
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

