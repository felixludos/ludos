
from ..mixins import Transactionable, Packable, Pullable
from humpack import tset, tdict, tlist, pack_member, unpack_member
from ..errors import MissingTypeError, MissingValueError, MissingObjectError, ObjectIDCollisionError
from .object import GameObject

from .. import util

class GameTable(Transactionable, Packable, Pullable):
	
	# TODO: maybe use singleton to allow access to table instance for anything that has access to the class GameTable
	# _instance = None
	# def __new__(cls, *args, **kwargs):
	# 	if cls._instance is None:
	# 		obj = super().__new__(cls, *args, **kwargs)
	# 		cls._instance = obj
	# 	return cls._instance
	
	def __init__(self):
		super().__init__()
		
		self.obj_types = tdict()
		self.ID_counter_shadow = None
		
		self.table = tdict()
		self.ID_counter = 0
		self.players = None
	
	def reset(self, ctrl):
		self.players = tlist(ctrl.manager)
	
	def in_transaction(self):
		return self.ID_counter_shadow is not None
	
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
		
		self.table.begin()
		self.ID_counter_shadow = self.ID_counter
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self.ID_counter_shadow = None
		self.table.commit()
		
	
	def abort(self):
		if not self.in_transaction():
			return

		self.ID_counter = self.ID_counter_shadow
		self.ID_counter_shadow = None
		self.table.abort()
	
	def get_ID(self):
		
		ID = str(self.ID_counter)
		
		while not self.is_available(ID):
			self.ID_counter += 1
			ID = str(self.ID_counter)
			
		self.ID_counter += 1
		return ID # always returns a str -> all IDs are str
	
	def populate(self, objects):
		for objname, info in objects.items():
			self.register_obj_type(name=objname, obj_cls=info['cls'],
			                       open=[] if info['open'] is None else info['open'],
			                       req=[] if info['req'] is None else info['req'],)
	
	def register_obj_type(self, obj_cls=None, name=None, open=[], req=[]):
		
		if obj_cls is None:
			assert name is not None, 'Must provide either a name or class'
			obj_cls = GameObject
		elif name is None:
			name = obj_cls.__name__
		
		self.obj_types[name] = tdict(obj_cls=obj_cls, open=tset(open), req=tset(req))
		
	def get_obj_types(self):
		return list(self.obj_types.keys())
	
	def create(self, obj_type, visible=None, ID=None,
	           **props):
		
		if obj_type in self.obj_types:
			info = self.obj_types[obj_type]
		else:
			raise MissingObjectError(obj_type)
		
		if ID is None:
			ID = self.get_ID()
		elif ID in self.table:
			raise ObjectIDCollisionError(ID)
		
		if visible is None:
			visible = tset(self.players)
		
		obj = info.obj_cls.__new__(info.obj_cls)
		
		obj._id = ID
		obj._table = self
		obj._open = info.open
		obj._req = info.req
		
		obj.__init__(obj_type=obj_type, visible=visible, **props)
		
		self.table[obj._id] = obj
		
		obj._verify()
		
		return obj
	
	def is_available(self, ID):
		return ID not in self.table
	
	# IMPORTANT: dev should use this function to create remove any game object
	def remove(self, obj):
		if obj in self.table:
			del self.table[obj]
		elif obj._id in self.table:
			del self.table[obj._id]
	
	def pull(self, player=None): # returns jsonified obj
		table = {}
		
		for k,v in self.table.items():
			table[k] = v.pull(player)
			
		return table
	
	def __pack__(self):
		
		data = {}
		data['ID_counter'] = self.ID_counter
		data['ID_counter_shadow'] = self.ID_counter_shadow
		data['table'] = {pack_member(k):pack_member(v)
		                 for k, v in self.table.items()}
		data['players'] = pack_member(self.players)
		data['obj_types'] = pack_member(self.obj_types)
		
		return data
	
	def __unpack__(self, data):
		
		self.__init__()
		
		self.obj_types = unpack_member(data['obj_types'])
		
		for k, x in data['table'].items():
			self.table[unpack_member(k)] = unpack_member(x)
			
		self.ID_counter = data['ID_counter']
		self.ID_counter_shadow = data['ID_counter_shadow']
		
		self.players = unpack_member(data['players'])
	
	def __getitem__(self, item):
		return self.table[item]
	
	def __setitem__(self, key, value):
		# assert isinstance(key, str), 'All IDs must be strings' # TODO: maybe remove for performance?
		self.table[key] = value
	
	def __delitem__(self, key):
		del self.table[key]
	
	# IMPORTANT: used to check whether object is still valid
	def __contains__(self, item):
		return item in self.table

