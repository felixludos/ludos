import sys, os
import yaml
import numpy as np
import random
import logging

from humpack import adict, tset, tlist, pack_member, unpack_member
from omnibelt import get_printer, get_global_settings, set_global_setting, load_yaml, save_yaml

from .mixins import Named, Typed, Jsonable, Packable, Transactionable, primitive
from .errors import UnknownElementError, InvalidKeyError, GameError

LIB_PATH = os.path.dirname(__file__)

def assert_(cond, info=None):
	if not cond:
		raise GameError(info)

def jsonify(obj, tfm=None):
	'''
	Convert from a nested python data structure (containing dict, set, list, tuples, humpack objects etc.)
	to a json conpatible object (only dicts, lists, and primitives).
	
	:param obj: Input data structure to be jsonified
	:param tfm: Custom transform function to jsonify special data structures (use with caution)
	:return: obj that can be transformed to json string using json.dump
	'''
	if tfm is not None:
		try:
			return tfm(obj, jsonify)
		except UnknownElementError:
			pass
	
	if isinstance(obj, primitive):
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
	'''
		Convert from a json readable python data structure (containing dict, list, tuples, humpack objects etc.)
		to a json conpatible object (only dicts, lists, and primitives).

		:param obj: Input data structure to be unjsonified
		:param tfm: Custom transform function to unjsonify certain data structures (use with caution)
	'''
	if tfm is not None:
		try:
			return tfm(obj, unjsonify)
		except UnknownElementError:
			pass
	if isinstance(obj, primitive):
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
		return adict({k: unjsonify(v, tfm=tfm) for k, v in obj.items()})
	
	raise UnknownElementError(obj)

def obj_unjsonify(obj, table=None):
	'''
	
	:param obj: data to be 
	:param table:
	:return:
	'''
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

def sort_by(ls, order):
	return tlist(x[0] for x in sorted(zip(ls,order),key=lambda x: x[1]))

def format_quantity(item, num=1, plural=None):
	if plural is None:
		plural = item + 's'
	if num == 0:
		return f'no {plural}'
	if num == 1:
		article = 'an' if item[0] in 'aeiouAEIOU8' else 'a'
		if item in {'11', '18'}:
			article = 'an'
		return f'{article} {item}'
	return f'{num} {plural}'

class RandomGenerator(Packable, Transactionable, random.Random):
	
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
	
	def __pack__(self):
		data = {}
		
		data['state'] = pack_member(self.getstate())
		if self._shadow is not None:
			data['_shadow'] = pack_member(self._shadow)
		
		return data
	
	def __unpack__(self, data):
		
		self._shadow = None
		
		x = unpack_member(data['state'])
		
		self.setstate(x)
		
		if '_shadow' in data:
			self._shadow = unpack_member(data['_shadow'])
		
	
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
	



















# class Empty(Packable, Transactionable):
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

