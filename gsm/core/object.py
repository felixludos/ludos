
import numpy as np
from itertools import chain
from ..errors import InvalidInitializationError, MissingValueError, UnknownElementError
from ..mixins import Named, Typed, Jsonable, Writable, Transactionable, Packable, Pullable, Hashable
from humpack import tset, tdict, tlist, tdeque, pack_member, unpack_member
from ..util import primitive, RandomGenerator, jsonify, get_printer
from ..io.registry import register_object

# TODO: fix so it works with cross referencing

prt = get_printer(__name__)

class GameObject(Typed, Writable, Jsonable, Pullable, tdict):
	
	def __init_subclass__(cls, game=None, name=None, open=None, req=None,
	                      req_table=None, obj_type=None, **kwargs):
		
		if obj_type is None:
			if name is not None: # acts as an alias to obj_type
				obj_type = name
			else:
				prt.warning('No obj_type provided for {}'.format(cls.__name__))
				obj_type = cls.__name__
		
		super().__init_subclass__(obj_type=obj_type, **kwargs)
		
		if req_table is not None:
			cls._req_table = req_table
		
		if game is not None:
			register_object(game=game, cls=cls, name=cls.obj_type, open=open, req=req)
	
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
		
		super().__init__(**props) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		self.visible = visible
		self.obj_type = obj_type
		
	def __getattribute__(self, item): # TODO clean up
		if item == 'obj_type' and 'obj_type' in self:
			return self['obj_type']
		return super().__getattribute__(item)
		
	# def _verify(self):
	# 	assert 'obj_type' in self
	# 	assert 'visible' in self
	# 	for req in self._req:
	# 		if req not in self:
	# 			raise MissingValueError(self.get_type(), req, *self._req)
		
	def __pack__(self):
		
		data = super().__pack__()
		data['_id'] = pack_member(self._id)
		data['_table'] = pack_member(self._table)
		data['_open'] = pack_member(self._open)
		data['_req'] = pack_member(self._req)
		
		return data
	
	def __unpack__(self, data):
		
		self._id = unpack_member(data['_id'])
		self._table = unpack_member(data['_table'])
		
		self._req = unpack_member(data['_req'])
		self._open = unpack_member(data['_open'])
		
		del data['_id']
		del data['_table']
		del data['_req']
		del data['_open']
		
		super().__unpack__(data)
	
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
				data[k] = jsonify(v)
				
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
		return self._add(*map(self._freed, objs))
	
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
		ID = '{}-{}'.format(self._id, hex(self._rng.getrandbits(32))[2:])
		
		if not self._table.is_available(ID):
			return self._gen_ID()
		return ID




