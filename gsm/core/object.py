
import numpy as np
from ..mixins import Named, Typed, Writable, Transactionable, Savable, Pullable
from ..basic_containers import tdict, tset, tlist


# TODO: fix so it works with cross referencing
def jsonify(obj):
	if isinstance(obj, GameObject):
		return {'_obj': obj._id}
	if isinstance(obj, list):
		return [jsonify(o) for o in obj]
	if isinstance(obj, dict):
		return {jsonify(k):jsonify(v) for k,v in obj.items()}
	if isinstance(obj, tuple):
		return {'_tuple': [jsonify(o) for o in obj]}
		# return [jsonify(o) for o in obj]
	if isinstance(obj, set):
		return {'_set': [jsonify(o) for o in obj]}
	if isinstance(obj, np.ndarray): # TODO: make this work for obj.dtype = 'obj', maybe recurse elements of .tolist()?
		return {'_ndarray': obj.tolist(), '_dtype':obj.dtype}
	return obj

def unjsonify(obj, obj_tbl=None):
	if isinstance(obj, list):
		return tlist([unjsonify(o) for o in obj])
	if isinstance(obj, dict):
		if '_obj' in obj and len(obj) == 1:
			if obj_tbl is None:
				return obj_tbl[obj['_obj']]
			else:
				return obj
		if '_set' in obj and len(obj) == 1:
			return tset([unjsonify(o) for o in obj['set']])
		if '_tuple' in obj and len(obj) == 1:
			return tuple(unjsonify(o) for o in obj['tuple'])
		if '_ndarray' in obj and '_dtype' in obj:
			return np.array(obj['_ndarray'], dtype=obj['_dtype'])
		return tdict({unjsonify(k):unjsonify(v) for k,v in obj.items()})
	return obj


class GameObject(Typed, Transactionable, Savable, Pullable):
	
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)
		
		self.__dict__['_id'] = None
		self.__dict__['_table'] = None
		
		self.__dict__['_open'] = None
		self.__dict__['_public'] = None
		self.__dict__['_hidden'] = None
		
		return self
	
	def __init__(self, ID, _table, visible, obj_type=None, _open=[], **props):
		
		if obj_type is None: # default obj_type is name of the class
			obj_type = self.__class__.__name__
		
		super().__init__(obj_type) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self._id = ID
		self._table = _table
		
		self._open = tset(_open)
		self._public = tdict(visible=visible, **props)
		self._hidden = tdict()
		
	def begin(self):
		if self.in_transaction():
			self.commit()
			
		self._open.begin()
		self._public.begin()
		self._hidden.begin()
	
	def in_transaction(self):
		return self._public.in_transaction()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._open.commit()
		self._public.commit()
		self._hidden.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._open.abort()
		self._public.abort()
		self._hidden.abort()
		
	def copy(self, ID=None):
		
		copy = self._table.create(self.get_type(), ID=ID, **self._public)
		
		copy._hidden = self._hidden.copy()
		copy._open = self._open.copy()
		
		return copy
		
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['_id'] = pack(self._id) # should always be a str though
		data['_table'] = pack(self._table)
		data['_open'] = pack(self._open)
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
		self._public = unpack(data['_public'])
		self._hidden = unpack(data['_hidden'])
		
		return self
		
	def pull(self, player=None):
		
		data = {}
		
		for k, v in self._public.items():
			if player is None or player in self.visible or k in self._open:
				data[k] = jsonify(v)
				
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
	
	
		


	
# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, ID, objs=None, **kwargs):
		super().__init__(ID, **kwargs)
		
		if objs is None:
			objs = []
		self.__dict__['_objs'] = objs
		
	# TODO: update
	# def __getstate__(self):
	# 	state = super().__getstate__()
	# 	state['_objs'] = [pack_savable(obj) for obj in self._objs]
	# 	return state
	#
	# def __setstate__(self, state):
	# 	self.__dict__['_objs'] = [unpack_savable(data) for data in state['_objs']]
	# 	del state['_objs']
	# 	super().__setstate__(state)
		
	# should not be overridden, and usually not called by dev
	def _registered(self, x):
		if self._table is not None:
			self._table.update(x._id, x)
		return x
	
	# should not be overridden, and usually not called by dev
	def _erased(self, x):
		if self._table is not None:
			self._table.remove(x._id)
		return x
	
	# should be overridden when subclassing
	def _get(self, n=None):
		raise NotImplementedError
	
	# should be overridden when subclassing
	def _add(self, objs):
		raise NotImplementedError
	
	# should not be overridden
	def get(self, n=None):
		
		xs = self._get(n)
		
		if n is None:
			xs = self._registered(xs)
		else:
			xs = [self._registered(x) for x in xs]
			
		return xs
	
	# should not be overridden
	def extend(self, objs):
		return self._add(self._erased(obj) for obj in objs)
	
	# should not be overridden
	def append(self, obj):
		return self._add([self._erased(obj)])
	
	
class SafeGenerator(GameObjectGenerator):
	pass # TODO: this should change the id of game objects when unregistering