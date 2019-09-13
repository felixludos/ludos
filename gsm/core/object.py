
from ..mixins import Named, Typed
from ..containers import tdict, tset, tlist, unpack_savable, pack_savable


class GameObject(Typed, tdict):
	
	def __init__(self, ID=None, obj_type=None, _table=None, visible=None, **kwargs):
		
		if obj_type is None: # default obj_type is name of the class
			obj_type = self.__class__.__name__
		
		super().__init__(obj_type, visible=visible, **kwargs) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self.__dict__['_id'] = ID
		self.__dict__['_table'] = _table
		
	def __getstate__(self):
		state = super().__getstate__()
		state['_id'] = self._id
		return state
	
	def __setstate__(self, state):
		self.__dict__['_id'] = state['_id']
		del state['_id']
		super().__setstate__(state)
		
	def __repr__(self):
		return '{}(ID={})'.format(self.__class__.__name__, self._id)


	
# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, ID, objs=None, **kwargs):
		super().__init__(ID, **kwargs)
		
		if objs is None:
			objs = []
		self.__dict__['_objs'] = objs
		
	def __getstate__(self):
		state = super().__getstate__()
		state['_objs'] = [pack_savable(obj) for obj in self._objs]
		return state
	
	def __setstate__(self, state):
		self.__dict__['_objs'] = [unpack_savable(data) for data in state['_objs']]
		del state['_objs']
		super().__setstate__(state)
		
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