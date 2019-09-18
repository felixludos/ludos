
from ..mixins import Transactionable, Savable
from ..basic_containers import tdict, tset, tlist
from ..signals import MissingTypeError, MissingValueError, MissingObjectError

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
		self.table = None
		self.ID_counter = None
		
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
	
	def get_ID(self):
		
		ID = str(self.ID_counter)
		
		while not self.is_available(ID):
			self.ID_counter += 1
			ID = str(self.ID_counter)
			
		self.ID_counter += 1
		return ID # always returns a str -> all IDs are str
	
	def is_available(self, ID):
		return ID not in self.table
	
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
	
	def __save(self):
		
		pack = self.__class__.__pack
		
		data = {}
		data['ID_counter'] = self.ID_counter
		data['table'] = {k:pack(v)
		                 for k, v in self.table.items()}
		
		return data
	
	@classmethod
	def __load(cls, data):
		
		unpack = cls.__unpack
		
		self = cls()
		
		for k, x in data['table'].items():
			self.table[k] = unpack(x)
			
		self.ID_counter = data['ID_counter']
		
		return self
	
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

