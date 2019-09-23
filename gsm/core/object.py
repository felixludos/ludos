
import numpy as np
from ..signals import InvalidInitializationError, MissingValueError, UnknownElementError
from ..mixins import Named, Typed, Writable, Transactionable, Savable, Pullable
from ..basic_containers import tdict, tset, tlist
from ..util import _primitives, RandomGenerator

# TODO: fix so it works with cross referencing
def obj_jsonify(obj):
	if isinstance(obj, _primitives):
		return obj
	if isinstance(obj, GameObject):
		return {'_obj': obj._id}
	if isinstance(obj, list):
		return [obj_jsonify(o) for o in obj]
	if isinstance(obj, dict):
		return {obj_jsonify(k):obj_jsonify(v) for k,v in obj.items()}
	if isinstance(obj, tuple):
		return {'_tuple': [obj_jsonify(o) for o in obj]}
		# return [jsonify(o) for o in obj]
	if isinstance(obj, set):
		return {'_set': [obj_jsonify(o) for o in obj]}
	if isinstance(obj, np.ndarray): # TODO: make this work for obj.dtype = 'obj', maybe recurse elements of .tolist()?
		return {'_ndarray': obj.tolist(), '_dtype':obj.dtype}
		
	raise UnknownElementError(obj)

def obj_unjsonify(obj, obj_tbl=None):
	if isinstance(obj, _primitives):
		return obj
	if isinstance(obj, list):
		return tlist([obj_unjsonify(o) for o in obj])
	if isinstance(obj, dict):
		if '_obj' in obj and len(obj) == 1:
			if obj_tbl is None:
				return obj_tbl[obj['_obj']]
			else:
				return obj
		if '_set' in obj and len(obj) == 1:
			return tset([obj_unjsonify(o) for o in obj['set']])
		if '_tuple' in obj and len(obj) == 1:
			return tuple(obj_unjsonify(o) for o in obj['tuple'])
		if '_ndarray' in obj and '_dtype' in obj:
			return np.array(obj['_ndarray'], dtype=obj['_dtype'])
		return tdict({obj_unjsonify(k):obj_unjsonify(v) for k,v in obj.items()})
	
	raise UnknownElementError(obj)


class GameObject(Typed, Writable, Transactionable, Savable, Pullable):
	
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)
		
		self.__dict__['_id'] = None
		self.__dict__['_table'] = None
		
		self.__dict__['_open'] = None
		self.__dict__['_req'] = None
		self.__dict__['_public'] = None
		self.__dict__['_hidden'] = None
		
		return self
	
	def __init__(self, **props):
		
		if self._id is None:
			InvalidInitializationError()
		
		super().__init__(**props) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self._verify()
		
	def _verify(self):
		for req in self._req:
			if req not in self:
				raise MissingValueError(self.get_type(), req, *self._req)
		
	def begin(self):
		if self.in_transaction():
			self.commit()
			
		self._public.begin()
		self._hidden.begin()
	
	def in_transaction(self):
		return self._public.in_transaction()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._public.commit()
		self._hidden.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._public.abort()
		self._hidden.abort()
		
	def copy(self, ID=None):
		
		copy = self._table.create(self.get_type(), ID=ID, **self._public)
		
		copy._hidden = self._hidden.copy()
		
		return copy
		
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['_id'] = pack(self._id) # should always be a str though
		data['_table'] = pack(self._table)
		data['_open'] = pack(self._open)
		data['_req'] = pack(self._req)
		data['_public'] = pack(self._public)
		data['_hidden'] = pack(self._hidden)
		
		return data
	
	@classmethod
	def __load(cls, data):
		
		self = cls.__new__(cls)
		unpack = cls.__unpack
		
		self._id = unpack(data['_id'])
		self._table = unpack(data['_table'])
		self._open = unpack(data['_open'])
		self._req = unpack(data['_req'])
		self._public = unpack(data['_public'])
		self._hidden = unpack(data['_hidden'])
		
		# self._verify() # TODO: maybe verify req when loading
		
		return self
		
	def get_text_type(self):
		return 'obj'
	def get_text_val(self):
		return self._id
	def get_text_info(self):
		return {'obj_type':self.get_type()}
	
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
			return key
		return self._public.__setattr__(key, value)
	
	def __delattr__(self, name):
		if name in self.__dict__:
			return super().__delattr__(name)
		return self._public.__delattr__(name)
	
	def __eq__(self, other):
		return self._id == other._id
	
		

# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, objs=[], default=GameObject, **props):
		super().__init__(**props)
		self._hidden.objs = tlist(objs)
		for obj in self._hidden.objs:
			assert 'obj_type' in obj, 'Every object in the Generator must have an "obj_type"'
		self._hidden.default = default
		self._hidden.ID_counter = 0
	
	######################
	# Do NOT Override
	######################
	
	def _registered(self, x):
		return self._table.create(ID=self._gen_ID(), **x)
	
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
		return self._add(*map(self._erased,objs))
	
	# should not be overridden
	def append(self, obj):
		return self._add(self._erased(obj))
	
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




