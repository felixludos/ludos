
from ..structures import Transactionable
from ..containers import tdict, tset, tlist

from .object import GameObject

class GameTable(Transactionable):
	
	def __init__(self, players):
		super().__init__()
		
		self.players = players
		self.table = tdict()
		self._in_transaction = False
		self.obj_types = tdict()
		
		self.reset()
	
	def in_transaction(self):
		return self._in_transaction
	
	def begin(self):
		if self.in_transaction():
			self.abort()
		
		self._in_transaction = True
		
		self.table.begin()
		self.created.begin()
		self.updated.begin()
		self.removed.begin()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self.table.commit()
		self.created.commit()
		self.updated.commit()
		self.removed.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self.table.abort()
		self.created.abort()
		self.updated.abort()
		self.removed.abort()
		
		
	def reset(self):
		self.created = tdict({player:tdict() for player in self.players})
		self.updated = tdict({player:tdict() for player in self.players})
		self.removed = tdict({player:tdict() for player in self.players})
		
	def register_obj_type(self, name, type):
		self.obj_types[name] = type
		
	def _get_type(self, obj_type=None):
		if obj_type is None or obj_type not in self.obj_types:
			return GameObject
		return self.obj_types[obj_type]
		
	def create(self, obj_type, visible=None, _id=None, **kwargs):
		
		if visible is None:
			visible = tset(self.players)
		
		otype = self._get_type(obj_type)
		
		obj = otype(obj_type=obj_type, visible=visible, **kwargs)
		
		if _id is not None:
			obj._id = _id
		
		self.table[obj._id] = obj
		self.created[obj._id] = obj
		
		return obj
	
	def update(self, key, value):
		self.table[key] = value
		self.updated[key] = value
	
	def remove(self, key):
		self.removed[key] = self.table[key]
		del self.table[key]
	
	def pull(self, player):
		
		
		
		pass
	
	def get_full(self, player=None):
		return self._format_table(self.table, player=player)
	def get_types(self):
		return self.obj_types.keys()
	
	def _format_table(self, table, player=None):
		pass
	
	def __getitem__(self, item):
		return self.objects[item]
	
	def __setitem__(self, key, value):
		self.objects[key] = value
		if key in self.objects:
			self.updated[key] = value
		else:
			self.created[key] = value
	
	def __delitem__(self, key):
		self.removed[key] = self.objects[key]
		del self.objects[key]

