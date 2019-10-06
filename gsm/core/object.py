
import numpy as np
from itertools import chain
from ..signals import InvalidInitializationError, MissingValueError, UnknownElementError
from ..mixins import Named, Typed, Jsonable, Writable, Transactionable, Savable, Pullable, Hashable
from humpack import tset, tdict, tlist
from ..util import _primitives, RandomGenerator, obj_jsonify

# TODO: fix so it works with cross referencing



class GameObject(Typed, Writable, Hashable, Jsonable, Transactionable, Savable, Pullable):
	
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)
		
		self.__dict__['_id'] = None
		self.__dict__['_table'] = None
		
		self.__dict__['_open'] = None
		self.__dict__['_req'] = None
		self.__dict__['_public'] = None
		self.__dict__['_hidden'] = None
		
		self.__dict__['_in_transaction'] = None
		
		return self
	
	def __init__(self, obj_type, visible, **props):
		
		if self._id is None:
			InvalidInitializationError()
		
		super().__init__(obj_type) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self._public.update(props)
		self._public.visible = visible
		self._verify()
		
	def _verify(self):
		assert 'obj_type' in self
		assert 'visible' in self
		for req in self._req:
			if req not in self:
				raise MissingValueError(self.get_type(), req, *self._req)
		
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
		
		self._in_transaction = True
		self._public.begin()
		self._hidden.begin()
	
	def in_transaction(self):
		return self._in_transaction
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self._public.commit()
		self._hidden.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self._public.abort()
		self._hidden.abort()
		
	def copy(self, ID=None):
		
		copy = self._table.create(self.get_type(), ID=ID, **self._public)
		
		copy._hidden = self._hidden.copy()
		
		return copy
		
	def jsonify(self):
		return {'_obj':self._id}
	
	def __iter__(self):
		return chain(iter(self._public), iter(self._hidden))
		
	def __save__(self):
		pack = self.__class__._pack_obj
		
		data = {}
		
		data['_id'] = pack(self._id) # should always be a str though
		data['_table'] = pack(self._table)
		data['_open'] = pack(self._open)
		data['_req'] = pack(self._req)
		data['_public'] = pack(self._public)
		data['_hidden'] = pack(self._hidden)
		
		return data
	
	def __load__(self, data):
		
		unpack = self.__class__._unpack_obj
		
		self._id = unpack(data['_id'])
		self._table = unpack(data['_table'])
		self._open = unpack(data['_open'])
		self._req = unpack(data['_req'])
		self._public = unpack(data['_public'])
		self._hidden = unpack(data['_hidden'])
		
		# self._verify() # TODO: maybe verify req when loading
		
	def get_text_type(self):
		return 'obj'
	def get_text_val(self):
		return str(self)
	def get_text_info(self):
		return {'obj_type':self.get_type(), 'ID':self._id}
	
	def pull(self, player=None):
		
		data = {}
		
		for k, v in self._public.items():
			if player is None or player in self.visible or k in self._open:
				data[k] = obj_jsonify(v)
				
		return data
	
	def __repr__(self):
		return '{}(ID={})'.format(self.get_type(), self._id)
	
	def __getattribute__(self, item): # TODO: test this! - behavior should default to self._public
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._public.__getattribute__(item)
		
	def __setattr__(self, key, value):
		if key in self.__dict__:
			return super().__setattr__(key, value)
		return self._public.__setattr__(key, value)
	
	def __getattr__(self, item):
		if item in self.__dict__:
			return super().__getattribute__(item)
		return self._public.__getattr__(item)
		try: # TODO: maybe allow accessing hidden values by default
			return self._public.__getattr__(item)
		except AttributeError:
			return self._hidden.__getattr__(item)
	
	def __delattr__(self, name):
		if name in self.__dict__:
			return super().__delattr__(name)
		if name in self._public:
			return self._public.__delattr__(name)
		if name in self._hidden:
			return self._hidden.__delattr__(name)
	
	def __getitem__(self, item):
		return self.__getattr__(item)
	
	def __setitem__(self, key, value):
		return self.__setattr__(key, value)
	
	def __delitem__(self, key):
		return self.__delattr__(key)
	
	def __contains__(self, item):
		return item in self._public or item in self._hidden
	
	def __eq__(self, other):
		try:
			return self._id == other._id
		except AttributeError:
			return False
	
	def __hash__(self):
		return hash(self._id)
	
		

# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, objs=[], default=None, **props):
		super().__init__(**props)
		self._hidden.objs = tlist(objs)
		if default is None:
			for obj in self._hidden.objs:
				assert 'obj_type' in obj, 'Every object in the Generator must have an "obj_type"'
		self._hidden.default = default
		self._hidden.ID_counter = 0
	
	######################
	# Do NOT Override
	######################
	
	def _registered(self, x):
		
		obj_type = self._hidden.default
		
		if 'obj_type' in x:
			obj_type = x.obj_type
			del x.obj_type
		
		return self._table.create(ID=self._gen_ID(), obj_type=obj_type, **x)
	
	def _freed(self, x):
		self._table.remove(x._id)
	
	# should not be overridden
	def get(self, n=None):
		objs = tlist(self._registered(x) for x in self._get(1 if n is None else n))
		
		if n is None:
			return objs[0]
		return objs
	
	# should not be overridden
	def extend(self, objs):
		return self._add(*map(self._freed,objs))
	
	# should not be overridden
	def append(self, obj):
		return self._add(self._freed(obj))
	
	######################
	# Must be Overridden
	######################
	
	# should be overridden when subclassing
	def _get(self, n=1):  # from self._hidden.objs to []
		raise NotImplementedError
	
	# should be overridden when subclassing
	def _add(self, *objs):  # from 'objs' to self._hidden.objs
		raise NotImplementedError
	
	######################
	# Optionally Overridden
	######################
	
	def _gen_ID(self):  # optionally overridden
		ID = '{}-{}'.format(self._id, self._hidden.ID_counter)
		self._hidden.ID_counter += 1
		
		if not self._table.is_available(ID):
			return self._gen_ID()
		return ID
	
	
class SafeGenerator(GameObjectGenerator):
	
	def __init__(self, seed, **rest):
		super().__init__(**rest)
		
		self._hidden.seed = seed
		self._hidden.rng = RandomGenerator(seed=seed)
		
	def _gen_ID(self):
		ID = '{}-{}'.format(self._id, hex(self._hidden.rng.getrandbits(32)))
		
		if not self._table.is_available(ID):
			return self._gen_ID()
		return ID




