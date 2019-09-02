
from ..mixins import Named, Typed
from ..containers import tdict, tset, tlist

class ZombieObjectException(Exception): # gets thrown when a SETTER is called from a GameObject even after it was removed from the game table
	def __init__(self, obj):
		super().__init__('{} has already beem removed from the GameTable'.format(repr(obj)))

class GameObject(Typed, tdict):
	
	def __init__(self, ID, obj_type=None, table=None, visible=None, **kwargs):
		
		if obj_type is None: # default obj_type is name of the class
			obj_type = self.__class__.__name__
		
		super().__init__(obj_type, visible=visible, _tracker=self, **kwargs) # all GameObjects are basically just tdicts with a obj_type and visible attrs and they can use a table to signal track changes
		
		self.__dict__['_id'] = ID
		self.__dict__['_table'] = table
		
	
	def signal(self): # signal to check if GameObject still exists
		if self._table is not None and self._table.check(self._id):
			raise ZombieObjectException
	
	def set_id(self, ID): # this is mostly to change the ID (not for initial set)
		if self._table is not None and '_id' in self.__dict__ and self._id in self._table:
			self._table.remove(self._id)
		
		self._id = ID
		
		if self._table is not None:
			self._table.update(self._id, self)
		
	def __repr__(self):
		return '{}(ID={})'.format(self.__class__.__name__, self._id)



	
	
# Generator - for card decks

class GameObjectGenerator(GameObject):
	
	def __init__(self, ID, objs=None, **kwargs):
		super().__init__(ID, **kwargs)
		
		if objs is None:
			objs = []
		self.__dict__['_objs'] = objs
		
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