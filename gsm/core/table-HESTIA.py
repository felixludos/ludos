
from ..mixins import Transactionable, Savable
from ..basic_containers import tdict, tset, tlist, pack_savable, unpack_savable
from ..signals import MissingTypeError, MissingValueError, MissingObjectError

from .object import GameObject
from .. import util

class GameTable(Transactionable, Savable):
	
	# TODO: maybe use singleton to allow access to table instance for anything that has access to the class GameTable
	# _instance = None
	# def __new__(cls, *args, **kwargs):
	# 	if cls._instance is None:
	# 		obj = super().__new__(cls, *args, **kwargs)
	# 		cls._instance = obj
	# 	return cls._instance
	
	def __init__(self):
		super().__init__()
		
		self._in_transaction = False
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
	
	# IMPORTANT: used to check whether object is still valid
	def check(self, key):
		return key in self.table
	
	# this function should usually be called automatically
	def update(self, key, value):
		self.table[key] = value
	
	# IMPORTANT: user should use this function to create remove any game object
	def remove(self, key):
		del self.table[key]
	
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
		if self.table is not None:
			data['table'] = {k:pack_savable(v)
			                 for k, v in self.table.items()}
		else:
			data['table'] = None
		
		return data
	
	def __setstate__(self, state):
		for obj_type in state['obj_types']:
			if obj_type not in self.obj_types:
				raise MissingTypeError(self, obj_type)
		
		self.reset(state['players'])
		
		if state['table'] is not None:
			for k, x in state['table'].items():
				self.table[k] = unpack_savable(x)
				self.table[k].__dict__['_table'] = self
				self._verify(self._get_type_info(self.table[k].get_type()).reqs,
				             self.table[k])
		else:
			state['table'] = None
			
		self.ID_counter = state['ID_counter']
	
	def __getitem__(self, item):
		return self.table[item]
	
	def __setitem__(self, key, value):
		self.table[key] = value
	
	def __delitem__(self, key):
		del self.table[key]
		
	def __contains__(self, item):
		return item in self.table

