
from git.gsm.old.structures import Transactionable
from ..containers import tdict, tset, tlist
from ..signals import MissingTypeError, MissingValueError, MissingObjectError

from .object import GameObject
from .. import util

class GameTable(Transactionable):
	
	def __init__(self):
		super().__init__()
		
		self._in_transaction = False
		self.obj_types = tdict()
		self.players = None
		self.table = None
		self.ID_counter = None
	
	def reset(self, players):
		self.table = tdict()
		self.ID_counter = 0
		
		self.players = players
	
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
	def register_obj_type(self, cls=None, name=None, required=None, visible=None):
		if cls is None:
			assert name is not None, 'Must provide either a name or class'
			cls = GameObject
		elif name is None:
			name = cls.__class__.__name__
		self.obj_types[name] = tdict(cls=cls,
		                             reqs=required, # props required for creating object
		                             visible=visible) # props visible to all players always (regardless of obj.visible)
		
	def _get_type_info(self, obj_type):
		if obj_type not in self.obj_types:
			raise MissingObjectError(obj_type)
		return self.obj_types[obj_type]
		
	# IMPORTANT: used to check whether object is still valid
	def check(self, key):
		return key in self.table
		
	# IMPORTANT: user should use this function to create new all game objects
	def create(self, obj_type, visible=None, ID=None, **props):
		
		info = self._get_type(obj_type)
		
		obj = self._create(info.cls, visible=visible, ID=ID, **props)
		self._verify(info.reqs, obj)
		
		return obj
	
	# only used from loading (no check for reqs)
	def _create(self, cls, ID=None, visible=None, **props):
		if visible is None:  # by default visible to all players
			visible = tset(self.players)
		
		if ID is None:
			ID = self.ID_counter
			self.ID_counter += 1
		
		obj = cls(ID=ID, obj_type=obj_type, visible=visible, **props)
		
		self.table[obj._id] = obj
		
		return obj
	
	def _verify(self, reqs, obj): # check that all requirements for a gameobject are satisfied
		if reqs is not None:
			for req in reqs:
				if req not in obj:
					raise MissingValueError(obj.get_type(), req, *reqs)
	
	# this function should usually be called automatically
	def update(self, key, value):
		self.table[key] = value
	
	# IMPORTANT: user should use this function to create remove any game object
	def remove(self, key):
		del self.table[key]
	
	def get_types(self):
		return self.obj_types.keys()
	
	def pull(self, player=None): # returns jsonified obj
		tbl = util.jsonify(self.table)
		if player is not None:
			self._privatize(tbl, player)
		return tbl
	def _privatize(self, tbl, player): # tbl must be a deep copy of self.table
		
		for ID, obj in tbl:
			for k, v in obj.items():
				allowed = self._get_type_info(k['obj_type']).visible
				if k != 'obj_type' and k != 'visible' and player not in obj['visible'] and (allowed is None or k not in allowed):
					del obj[k] # remove information not permitted
	
	def __getstate__(self):
		
		data = {}
		
		data['players'] = self.players
		data['obj_types'] = list(self.obj_types.keys())
		data['ID_counter'] = self.ID_counter
		data['table'] = {k:v.__getstate__()
		                 for k, v in self.table.items()}
		
		return data
	
	def __setstate__(self, state):
		for obj_type in state['obj_types']:
			if obj_type not in self.obj_types:
				raise MissingType(self, obj_type)
		
		self.reset(state['players'])
		
		for k, x in state['table'].items():
			info = self._get_type_info(x['_data']['obj_type']) # works because all elements in table are GameObjects --> tdict
			self.table[k] = self._create(info.cls)
			self.table[k].__setstate__(x)
			self._verify(info.reqs, self.table[k])
			
		self.ID_counter = state['ID_counter']
	
	def __getitem__(self, item):
		return self.table[item]
	
	def __setitem__(self, key, value):
		self.table[key] = value
	
	def __delitem__(self, key):
		del self.table[key]
		
	def __contains__(self, item):
		return item in self.table

