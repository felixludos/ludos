
from .arg_dict import adict
from .common import condensed_str
from weakref import WeakValueDictionary
from .transactions import TransactionableObject
from itertools import chain

# idict - dicts with ID (copy creates new id)

# _object_table = WeakValueDictionary()
# def get_table():
# 	return _object_table
# def get_object(ID):
# 	return _object_table[ID]
# def del_object(obj):
# 	del _object_table[obj._id]
#
#
_dict_ID = 0
def pull_ID():
	global _dict_ID
	out = _dict_ID
	_dict_ID += 1
	return out
#
# def register_obj(obj, ID=None):
# 	if ID is None:
# 		try: # using already existing ID
# 			ID = obj._id
# 		except AttributeError:
# 			ID = pull_ID()
# 	assert ID not in _object_table, 'There is already an object registered with ID: {}'.format(ID)
# 	_object_table[ID] = obj
# 	return ID

class iddict(adict): # WARNING: These objects are not garbage collected
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		ID = pull_ID()
		
		if '_id' in self:
			ID = self['_id']
			del self['_id']
			
		self.__dict__['_id'] = ID
		
		# print(self)
		
		#_object_table[self._id] = self # dont use object registry
	def __getattr__(self, key):
		if key == '_id':
			return self.__dict__['_id']
		return super().__getattr__(key)
	def __eq__(self, other):
		return self._id == other._id
	def __hash__(self):
		return hash(self._id)
	def __len__(self):
		return max(0, super().__len__( ) -1)
	# def __del__(self):
	# 	del _object_table[self._id]
	def __getstate__(self):
		return super().__getstate__()
	def copy(self):
		copy = idict(self.items())
		copy.__dict__['_id'] = self.__dict__['_id']
		return copy
	def to_dict(self, with_id=True):
		if with_id:
			copy = dict(self.items())
			copy['_id'] = self._id
			return copy
		return dict(self.items())
	def __str__(self):
		items = []
		for k ,v in self.items():
			items.append( '{}:{}'.format(str(k), condensed_str(v)) )
		return 'idict[{}]({})'.format(self._id, ', '.join(items))
	def __repr__(self):
		return '{ ' +', '.join('{}:{}'.format(repr(k) ,repr(v)) for k ,v in self.items() ) +'}'


def idict(*args, **kwargs):
	return TransactionableObject(iddict(*args, **kwargs), lambda x: iter(chain(x.keys(), x.values())))

