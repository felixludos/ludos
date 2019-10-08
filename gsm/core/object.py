
import numpy as np
from itertools import chain
from ..signals import InvalidInitializationError, MissingValueError, UnknownElementError
from ..mixins import Named, Typed, Jsonable, Writable, Transactionable, Savable, Pullable, Hashable
from humpack import tset, tdict, tlist, tdeque
from ..util import _primitives, RandomGenerator, obj_jsonify

# TODO: fix so it works with cross referencing

class GameObject(Typed, Writable, Jsonable, Pullable, tdict):
	
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)
		
		self.__dict__['_id'] = None
		self.__dict__['_table'] = None
		
		self.__dict__['_open'] = None
		self.__dict__['_req'] = None
		
		return self
	
	def __init__(self, obj_type, visible, **props):
		
		if self._id is None:
			InvalidInitializationError()
		
		super().__init__(obj_type, **props) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self.visible = visible
		self._verify()
		
	def _verify(self):
		assert 'obj_type' in self
		assert 'visible' in self
		for req in self._req:
			if req not in self:
				raise MissingValueError(self.get_type(), req, *self._req)
		
	def __save__(self):
		pack = self.__class__._pack_obj
		
		data = super().__save__()
		data['_id'] = pack(self._id)
		data['_table'] = pack(self._table)
		data['_open'] = pack(self._open)
		data['_req'] = pack(self._req)
		
		return data
	
	def __load__(self, data):
		unpack = self.__class__._unpack_obj
		
		self._id = unpack(data['_id'])
		self._table = unpack(data['_table'])
		
		self._req = unpack(data['_req'])
		self._open = unpack(data['_open'])
		
		del data['_id']
		del data['_table']
		del data['_req']
		del data['_open']
		
		super().__load__(data)
	
		# self._verify() # TODO: maybe verify req when loading
	
	def copy(self, ID=None):
		return self._table.create(self.get_type(), ID=ID, **self)
		
	def jsonify(self):
		return {'_obj':self._id}
		
	def get_text_type(self):
		return 'obj'
	def get_text_val(self):
		return str(self)
	def get_text_info(self):
		return {'obj_type':self.get_type(), 'ID':self._id}
	
	def pull(self, player=None):
		
		data = {}
		
		for k, v in self.items():
			if k[0] != '_' and \
					(player is None
					 or player in self.visible
					 or k in self._open):
				data[k] = obj_jsonify(v)
				
		return data
	
	def __repr__(self):
		return '{}(ID={})'.format(self.get_type(), self._id)
	
	def __str__(self):
		return '{}[{}]'.format(self.get_type(), self._id)
	
	def __eq__(self, other):
		try:
			return self._id == other._id
		except AttributeError:
			return False
	def __ne__(self, other):
		try:
			return self._id != other._id
		except AttributeError:
			return True
	
	
	def __hash__(self):
		return hash(self._id)
	
		

# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, objs, default=None, **props):
		super().__init__(**props)
		self._objs = objs
		if default is None:
			for obj in self._objs:
				assert 'obj_type' in obj, 'Every object in the Generator must have an "obj_type"'
		self._default = default
		self._ID_counter = 0
	
	######################
	# Do NOT Override
	######################
	
	def _registered(self, x):
		
		obj_type = self._default
		
		if 'obj_type' in x:
			obj_type = x.obj_type
			del x.obj_type
		
		return self._table.create(ID=self._gen_ID(), obj_type=obj_type, **x)
	
	def _freed(self, x):
		self._table.remove(x)
	
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
	def _get(self, n=1):  # from self._objs to []
		raise NotImplementedError
	
	# should be overridden when subclassing
	def _add(self, *objs):  # from 'objs' to self._objs
		raise NotImplementedError
	
	######################
	# Optionally Overridden
	######################
	
	def _gen_ID(self):  # optionally overridden
		ID = '{}-{}'.format(self._id, self._ID_counter)
		self._ID_counter += 1
		
		if not self._table.is_available(ID):
			return self._gen_ID()
		return ID
	
	
class SafeGenerator(GameObjectGenerator):
	
	def __init__(self, seed, **rest):
		super().__init__(**rest)
		
		self._seed = seed
		self._rng = RandomGenerator(seed=seed)
		
	def _gen_ID(self):
		ID = '{}-{}'.format(self._id, hex(self._rng.getrandbits(32)))
		
		if not self._table.is_available(ID):
			return self._gen_ID()
		return ID




