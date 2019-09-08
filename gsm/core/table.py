
from ..structures import Transactionable
from ..containers import tdict, tset, tlist

from .object import GameObject

class GameTable(Transactionable):
	
	def __init__(self, players):
		super().__init__()
		
		self.players = players
		self._in_transaction = False
		self.obj_types = tdict()
		
		self.reset()
	
	def reset(self):
		self.table = tdict()
		self.ID_counter = 0
	
	def in_transaction(self):
		return self._in_transaction
	
	def begin(self):
		if self.in_transaction():
			self.abort()
		
		self._in_transaction = True
		self.table.begin()
	
	def commit(self):
		if not self.in_transaction():
			return
		self.table.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		self.table.abort()
		
	# IMPORTANT: user can optionally register their own defined subclasses of GameObject here for them to be used
	def register_obj_type(self, cls, name=None):
		if name is None:
			name = cls.__class__.__name__
		self.obj_types[name] = cls
		
	def _get_type(self, obj_type=None):
		if obj_type is None:
			return GameObject
		elif obj_type not in self.obj_types:
			return obj_type
		return self.obj_types[obj_type]
		
	# IMPORTANT: used to check whether object is still valid
	def check(self, key):
		return key in self.table
		
	# IMPORTANT: user should use this function to create new all game objects
	def create(self, obj_type, visible=None, ID=None, **kwargs):
		
		if visible is None: # by default visible to all players
			visible = tset(self.players)
		
		otype = self._get_type(obj_type)
		
		if ID is None:
			ID = self.ID_counter
			self.ID_counter += 1
		
		obj = otype(ID=ID, obj_type=obj_type, visible=visible, **kwargs)
		
		self.table[obj._id] = obj
		
		return obj
	
	# this function should usually be called automatically
	def update(self, key, value):
		self.table[key] = value
	
	# IMPORTANT: user should use this function to create remove any game object
	def remove(self, key):
		del self.table[key]
	
	def get_types(self):
		return self.obj_types.keys()
	
	def pull(self):
		return self.table
	
	def __getitem__(self, item):
		return self.table[item]
	
	def __setitem__(self, key, value):
		self.table[key] = value
	
	def __delitem__(self, key):
		del self.table[key]

