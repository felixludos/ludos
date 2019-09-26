import time
from gsm.util import _primitives
from gsm.signals import SavableClassCollisionError, ObjectIDReadOnlyError, UnregisteredClassError

class S(object):
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

	def __new__(cls, *args, **kwargs):
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
	def pack(cls, obj): # top-level for dev/user to call

		# savefile contains
		assert cls.__ref_table is None, 'There shouldnt be a object table already here'
		cls.__ref_table = {} # create object table

		out = cls._pack_obj(obj)

		# additional meta info
		meta = {}
		meta['timestamp'] = time.strftime('%Y-%m-%d_%H%M%S')

		data = {
			'table': cls.__ref_table,
			'meta': meta,
		}

		cls.__ref_table = None  # clear built up object table

		# save parent object separately
		if isinstance(obj, S):
			data['ref'] = obj.__getref()
		else:
			data['obj'] = out

		return data

	@classmethod
	def unpack(cls, data, meta=False):
		# add the current cls.__ID_counter to all loaded objs
		cls.__ref_table = data['table']
		cls.__obj_table = {}

		obj = cls._unpack_obj(data['table'][data['ref']] if 'ref' in data else data['obj'])

		cls.__ref_table = None
		cls.__obj_table = None

		if meta:
			return obj, data['meta']
		return obj

	@classmethod
	def _pack_obj(cls, obj):
		refs = cls.__ref_table

		if isinstance(obj, _primitives):
			return obj
		elif isinstance(obj, S):
			if refs is not None:
				ref = obj.__getref()
				if ref not in refs:
					refs[ref] = obj._save_obj()
					# refs[ref] = { obj._save_obj() }

				return {'_type': S._full_name(obj.__class__), '_ref': ref}

			assert False, 'must save using Savable.pack(obj)'
			return {'_type': S._full_name(obj.__class__), '_data': obj._save_obj()}

		elif issubclass(obj, S):
			return {'_type': '_class', '_data': S._full_name(obj)}

		elif type(obj) == dict:
			# raise NotImplementedError
			return {'_type': '_dict', '_data':{k:cls._pack_obj(v) for k,v in obj.items()}}
		elif type(obj) == list:
			# raise NotImplementedError
			return {'_type': '_list', '_data':[cls._pack_obj(x) for x in obj]}
		elif type(obj) == set:
			# raise NotImplementedError
			return {'_type': '_set', '_data': [cls._pack_obj(x) for x in obj]}
		elif type(obj) == tuple:
			# raise NotImplementedError
			return {'_type': '_tuple', '_data': [cls._pack_obj(x) for x in obj]}

		else:
			raise TypeError('Un recognized type: {}'.format(type(obj)))

	@classmethod
	def _unpack_obj(cls, data):
		refs = cls.__ref_table
		objs = cls.__obj_table

		if isinstance(data, _primitives):
			return data
		else:
		# if isinstance(data, dict) and '_type' in data:
			typ = data['_type']
			if typ == '_class':
				return cls.get_cls(data['_data'])

			elif typ == '_dict':
				# raise NotImplementedError
				return {k:cls._unpack_obj(v) for k,v in data['_data'].items()}
			elif typ == '_list':
				# raise NotImplementedError
				return [cls._unpack_obj(x) for x in data['_data']]
			elif typ == '_set':
				# raise NotImplementedError
				return {cls._unpack_obj(x) for x in data['_data']}
			elif typ == '_tuple':
				# raise NotImplementedError
				return tuple(cls._unpack_obj(x) for x in data['_data'])

			else: # Savable instance
				ID = data['_ref']
				if ID in objs:
					return objs[ID]
				else:
					new = cls.get_cls(typ)
					obj = new._load_obj(refs[ID])

					# move ID from refs to objs - it has been loaded
					del refs[ID]
					objs[ID] = obj

					return obj



	def __getref(self):
		return self.__dict__[self.__class__.__savable_id_attr]

	def __deepcopy__(self, memodict={}):
		return self.__class__.unpack(self.__class__.pack(self))

	# functions must be overridden => any information in an instance that should be saved/loaded that could be anything other than a primitive should be packed/unpacked using self.__class__.__pack and self.__class__.__unpack

	def _save_obj(self): # should call self.__class__.__pack(obj) on all objects that are relevant to its state
		raise NotImplementedError

	@classmethod
	def _load_obj(cls, data): # should call cls.__unpack(obj) on all objects that are relevant to its state and return an instance
		raise NotImplementedError


class A(S):
	def __init__(self, x=1, y=2):
		super().__init__()
		self.x = x
		self.y = y
	
	def __repr__(self):
		return 'A({},{})'.format(self.x, self.y)
	
	def _save_obj(self):
		pack = self.__class__._pack_obj
		
		data = {}
		
		data['x'] = pack(self.x)
		data['y'] = pack(self.y)
		
		return data
	
	@classmethod
	def _load_obj(cls, data):
		unpack = cls._unpack_obj
		
		self = cls()
		
		self.x = unpack(data['x'])
		self.y = unpack(data['y'])
		
		return self
