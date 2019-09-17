
import time
import numpy as np
from .signals import UnregisteredClassError, SavableClassCollisionError, ObjectIDReadOnlyError

_primitives = (type(None), str, int, float, bool) # all json readable and no sub elements

class Savable(object):
	__subclasses = {}
	__obj_id_counter = 0
	__savable_id_attr = '_pack_id' # instances of all subclasses cant use this identifier as an attribute
	
	# temporary data for saving/loading
	__obj_table = None
	__ref_table = None
	
	def __init_subclass__(cls, *args, **kwargs):
		super().__init_subclass__()
		name = cls._full_name(cls)
		if name in cls.__subclasses:
			raise SavableClassCollisionError(name, cls)
		cls.__subclasses[name] = cls
		# cls._subclasses[cls.__name__] = cls
		
	def __new__(cls):
		obj = super().__new__(cls)
		obj.__dict__[cls.__savable_id_attr] = cls.__obj_id_counter # TODO: make thread safe (?)
		cls.__obj_id_counter += 1
		return obj
	
	def __setattr__(self, key, value):
		if key == self.__class__.__savable_id_attr:
			raise ObjectIDReadOnlyError()
		return super().__setattr__(key, value)
		
	@staticmethod
	def _full_name(cls):
		name = cls.__name__
		module = cls.__module__
		if module is None:
			return name
		return '.'.join([module, name])

	@classmethod
	def get_cls(cls, name):
		try:
			return cls.__subclasses[name]
		except KeyError:
			raise UnregisteredClassError(name)

	@classmethod
	def create(cls, name):
		if name not in cls.__subclasses:
			raise UnregisteredClassError(name)
		new = cls.__subclasses[name]
		return new.__new__(new) # avoid calling __init__ incase of required args

	@classmethod
	def pack(cls, obj): # top-level for dev/user to call
		
		# savefile contains
		assert cls.__ref_table is None, 'There shouldnt be a object table already here'
		cls.__ref_table = {} # create object table
		
		out = cls.__pack(obj)
		
		# additional meta info
		meta = {}
		meta['timestamp'] = time.strftime('%Y-%m-%d_%H%M%S')
		
		data = {
			'table': cls.__ref_table,
			'meta': meta,
		}
		
		cls.__ref_table = None  # clear built up object table
		
		# save parent object separately
		if isinstance(obj, Savable):
			data['ref'] = obj.__getref()
		else:
			data['obj'] = out
		
		return data
	
	@classmethod
	def unpack(cls, data, meta=False):
		# add the current cls.__ID_counter to all loaded objs
		cls.__ref_table = data['table']
		cls.__obj_table = {}
		
		obj = cls.__unpack(data['table'][data['ref']] if 'ref' in data else data['obj'])
		
		cls.__ref_table = None
		cls.__obj_table = None
		
		if meta:
			return obj, data['meta']
		return obj

	@classmethod
	def __pack(cls, obj):
		refs = cls.__ref_table
		
		if isinstance(obj, Savable):
			if refs is not None:
				ref = obj.__getref()
				if ref not in refs:
					refs[ref] = obj.__save()
				
				return {'_type': Savable._full_name(obj.__class__), '_ref': ref}
				
			assert False, 'must save using Savable.pack(obj)'
			return {'_type': Savable._full_name(obj.__class__), '_data': obj.__save()}
		
		elif issubclass(obj, Savable):
			return {'_type': '_class', '_data': Savable._full_name(obj)}
		else:
			assert isinstance(obj, _primitives), 'Invalid type: {}'.format(type(obj))
			return obj
	
	@classmethod
	def __unpack(cls, data):
		refs = cls.__class__.__ref_table
		objs = cls.__class__.__obj_table
		
		if isinstance(data, _primitives):
			return data
		else:
		# if isinstance(data, dict) and '_type' in data:
			typ = data['_type']
			if typ == '_class':
				return cls.get_cls(data['_data'])
			else: # Savable instance
				ID = data['_ref']
				if ID in objs:
					return objs[ID]
				else:
					new = cls.get_cls(typ)
					obj = new.__new__(new) # create instance without calling __init__
					obj.__load(refs[ID])
					
					# move ID from refs to objs - it has been loaded
					del refs[ID]
					objs[ID] = obj
					
					return obj
		
	
	
	def __getref(self):
		return self.__dict__[self.__class__.__savable_id_attr]
	
	def __deepcopy__(self, memodict={}):
		return self.__class__.unpack(self.__class__.pack(self))
	
	# functions must be overridden => any information in an instance that should be saved/loaded that could be anything other than a primitive should be packed/unpacked using self.__class__.__pack and self.__class__.__unpack
	
	def __save(self): # should call self.__class__.__pack(obj) on all objects that are relevant to its state
		raise NotImplementedError
	
	def __load(self, data): # should call self.__class__.__unpack(obj) on all objects that are relevant to its state
		raise NotImplementedError

class Named(object):
	def __init__(self, name=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
	
	def __str__(self):
		return self.name

class Typed(object):
	def __init__(self, obj_type=None, **kwargs):
		super().__init__(**kwargs)
		self.obj_type = obj_type
	
	def get_type(self):
		return self.obj_type


class Transactionable(object):
	
	def begin(self):
		raise NotImplementedError
	
	def in_transaction(self):
		raise NotImplementedError
	
	def commit(self):
		raise NotImplementedError
	
	def abort(self):
		raise NotImplementedError

	# def __enter__(self):
	# 	# self._context = True
	# 	self.begin()
	#
	# def __exit__(self, type, *args):
	# 	# self._context = False
	# 	if type is None:
	# 		self.commit()
	# 	else:
	# 		self.abort()
	# 	return None if type is None else type.__name__ == 'AbortTransaction'

class Container(Transactionable, Savable): # containers are Savable over Transactionable - ie. transactions are part of the state, so setting the state can change the transaction
	pass


# class Trackable(object):
#
# 	def __init__(self, tracker=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self.__dict__['_tracker'] = tracker  # usually should be set manually --> by GameObject
#
# 	def signal(self, *args, **kwargs):  # for tracking
# 		if self._tracker is not None:
# 			return self._tracker.signal(*args, **kwargs)