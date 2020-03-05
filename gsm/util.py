import sys, os
import yaml
import numpy as np
import random
import logging
from humpack import tdict, tset, tlist, pack_member, unpack_member

from .mixins import Named, Typed, Jsonable, Packable, Transactionable, primitive
from .errors import UnknownElementError, InvalidKeyError, GameError

LIB_PATH = os.path.dirname(__file__)

log_levels = {
	'debug': logging.DEBUG,
	'info': logging.INFO,
	'warning': logging.WARNING,
	'error': logging.ERROR,
	'critical': logging.CRITICAL,
}

_global_settings = { # primarily for logging
	'level': 'debug',
	'logfile': os.path.join(os.path.dirname(LIB_PATH), 'logs', 'test.log'),
	'format': '%(levelname)s:%(name)s: %(msg)s',
	'stream': True,
}

def get_global_settings():
	return _global_settings.copy()

def set_global_setting(key, value):
	_global_settings[key] = value

def get_printer(name, level=None, format=None, formatter=None,
				
				no_file=None, file_handler=None,
                filelevel=None, fileformatter=None, filepath=None,
                
				include_stream=None, stream_handler=None,
                stream_level=None, stream_formatter=None,
                
                ):
	'''
	Create a logger possibly writing records to both a file and stdout (aka streaming).
	For any unspecified arguments, the global settings are consulted.
	
	:param name:
	:param level:
	:param format:
	:param formatter:
	:param no_file:
	:param file_handler:
	:param filelevel:
	:param fileformatter:
	:param filepath:
	:param include_stream:
	:param stream_handler:
	:param stream_level:
	:param stream_formatter:
	:return:
	'''
	
	if include_stream is None:
		include_stream = _global_settings['stream']
	if no_file is None:
		no_file = 'logfile' in _global_settings and _global_settings['logfile'] is not None
	
	assert not no_file or include_stream, 'Not logging anywhere'
	
	logger = logging.getLogger(name)
	
	if level is None:
		level = _global_settings['level']
	
	logger.setLevel(log_levels[level] if level in log_levels else level)
	
	if format is None: # default formatter
		format = _global_settings['format']
	if formatter is None:
		formatter = logging.Formatter(format)
	
	if filepath is None and 'logfile' in _global_settings and _global_settings['logfile'] is not None:
		filepath = _global_settings['logfile']
	
	if file_handler is None and not no_file and filepath is not None: # create default file_handler
		
		if fileformatter is None:
			fileformatter = formatter
		
		if filelevel is None:
			filelevel = level
		
		file_handler = logging.FileHandler(filepath)
		file_handler.setLevel(log_levels[filelevel] if filelevel in log_levels else filelevel)
		file_handler.setFormatter(fileformatter)
		
	if file_handler is not None:
		logger.addHandler(file_handler)
	
	if stream_handler is None and include_stream: # create default stream_handler
		
		if stream_level is None:
			stream_level = level
		
		if stream_formatter is None:
			stream_formatter = formatter
		
		stream_handler = logging.StreamHandler()
		stream_handler.setLevel(log_levels[stream_level] if stream_level in log_levels else stream_level)
		stream_handler.setFormatter(stream_formatter)
	
	if stream_handler is not None:
		logger.addHandler(stream_handler)

	return logger

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
		return tdict({k: unjsonify(v, tfm=tfm) for k, v in obj.items()})
	
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

