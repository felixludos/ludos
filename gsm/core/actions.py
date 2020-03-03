# import json
from itertools import product, chain
from humpack import tset, tdict, tlist, pack_member, unpack_member
from .object import GameObject
from .player import GamePlayer
from ..mixins import Typed, Named, Transactionable, Packable, Pullable, Hashable
from ..errors import ActionMismatch, UnknownActionElement, InvalidActionError
from ..writing import write, writef
from ..util import jsonify


def _expand_actions(code):
	if isinstance(code, set) and len(code) == 1:
		return _expand_actions(next(iter(code)))
	
	if isinstance(code, dict) or isinstance(code, ActionElement) or isinstance(code, str) or isinstance(code, int):
		return [code]
	
	# tuple case
	if isinstance(code, (tuple, list)):
		return list(product(*map(_expand_actions, code)))
	if isinstance(code, set):
		return chain(*map(_expand_actions, code))
	return code
def _flatten(bla):
	output = ()
	for item in bla:
		output += _flatten(item) if isinstance(item, (tuple, list)) else (item,)
	return output
def decode_action_set(code):
	code = _expand_actions(code)
	return tset(map(_flatten, code))


def process_actions(raw): # process input when saving new action set (mostly turn options into ActionElement instances)
	
	if isinstance(raw, tuple):
		return tuple(process_actions(r) for r in raw)
	if isinstance(raw, set):
		return tset(process_actions(r) for r in raw)
	
	if isinstance(raw, ActionElement):
		return raw
	if isinstance(raw, GameObject):
		return ObjectAction(raw)
	if isinstance(raw, GamePlayer):
		return PlayerAction(raw)
	if isinstance(raw, (str, int, float, bool)):
		return FixedAction(raw)
	if type(raw).__module__ == 'numpy': # unwrap numpy types
		return process_actions(raw.item())
	
	
	raise UnknownActionElement(raw)
	

def format_actions(raw): # format action sets to be sent to frontend (mostly encoding ActionElements)
	
	if isinstance(raw, tuple):
		return {'_tuple': [format_actions(r) for r in raw]}
	if isinstance(raw, set):
		return {'_set': [format_actions(r) for r in raw]}
	
	if isinstance(raw, ActionElement):
		info = raw.encode()
		info['type'] = raw.get_type()
		return info
		
	# all leaf elements must be ActionElement instances
	
	raise UnknownActionElement(raw)



class GameActions(Packable, Pullable): # created and returned in phases
	
	def __init__(self, status=None):
		super().__init__()
		self._current = None
		self._options = tdict()
		self._name = None
		self._desc = None
		
		self.set_status(status)
		self.info = tdict() # should be accessed directly by dev
	
	def set_status(self, status):
		if isinstance(status, str):
			status = write(status)
		self.status = status
		
		# if txt is not None:
		# 	status = writef(txt, *objs, end=end, indent_level=indent_level, **kwobjs)
		# else:
		# 	status = None
	
	def in_transaction(self):
		return self._current is not None
	
	def begin(self, name, desc=None):
		if self.in_transaction():
			return
		
		# assert name is not None, 'must specify a name'
		
		self.set_name(name)
		self.set_desc(desc)
		self._current = tset()

	def commit(self):
		if not self.in_transaction():
			return
		
		if len(self._current):
			opt = tdict(actions=process_actions(self._current))
			if self._desc is not None:
				opt.desc = self._desc
			self._options[self._name] = opt
		
		self._name = None
		self._desc = None
		self._current = None

	def abort(self):
		if not self.in_transaction():
			return

		self._current = None
		self._name = None
		self._desc = None
	
	def __enter__(self):
		self.begin(self._name, self._desc)

	def __exit__(self, type, *args):
		if type is None:
			self.commit()
		else:
			self.abort()
		return None if type is None else type.__name__ == 'AbortTransaction'
		
	def set_name(self, name):
		self._name = name
		
	def set_desc(self, desc):
		if desc is not None and isinstance(desc, str):
			desc = write(desc)
		self._desc = desc
		
	def __call__(self, name, desc=None):
		self.set_name(name)
		self.set_desc(desc)
		return self
	
	def add(self, *items):
		if not self.in_transaction():
			raise Exception('Call begin() to start new action group')
		self._current.add(items)
	
	def __pack__(self):
		
		data = {}
		
		data['_current'] = pack_member(self._current)
		data['_desc'] = pack_member(self._desc)
		data['_options'] = pack_member(self._options)
		data['status'] = pack_member(self.status)
		data['info'] = pack_member(self.info)
		data['_name'] = pack_member(self._name)
		
		return data
	
	def __unpack__(self, data):
		
		self._current = unpack_member(data['_current'])
		self._desc = unpack_member(data['_desc'])
		self._options = unpack_member(data['_options'])
		self.status = unpack_member(data['status'])
		self.info = unpack_member(data['info'])
		self._name = unpack_member(data['_name'])
	
	def verify(self, name, action): # action should be a tuple
		
		option = self._options[name]
		actionset = decode_action_set(option.actions)
		
		for tpl in actionset:
			if len(tpl) == len(action):
				try:
					out = ActionTuple(name, (elm.evaluate(a) for elm, a in zip(tpl, action)))
				except ActionMismatch:
					pass # action didnt match
				else:
					return out
					
		raise InvalidActionError(action)
	
	def __len__(self):
		return len(self._options)
	
	def __add__(self, other):
		new = GameActions()
		new._options.update(self._options)
		new._options.update(other._options)
		new.status = self.status if self.status is not None else other.status
		return new
		
	def get_info(self):
		return self.info
	
	def pull(self): # returns jsonified obj
		
		options = {}
		for name, group in self._options.items():
			opt = {'actions': format_actions(group.actions)}
			if 'desc' in group:
				opt['desc'] = group.desc
			options[name] = opt
		
		out = {
			'options': options,
		}
		
		if self.status is not None:
			out['status'] = self.status
			
		if len(self.info):
			out['info'] = jsonify(self.info)
			
		return out


# Advanced action queries

class ActionTuple(tuple):
	def __new__(cls, name, tpl):
		return super().__new__(cls, tpl)
	def __init__(self, group, tpl):
		self.obj_type = group
		
	def get_type(self):
		return self.obj_type

class ActionElement(Typed, Transactionable, Packable, Hashable):
	
	def encode(self):
		raise NotImplementedError
	
	def evaluate(self, q): # either returns element or raises ActionMismatch
		raise NotImplementedError

class FixedAction(ActionElement, obj_type='fixed'):
	def __init__(self, val): # works for primitives
		# super().__init__(type(val).__name__)
		super().__init__()
		self.val = val

	def __pack__(self):
		return self.val

	def __unpack__(self, data):
		self.__init__(data)

	def encode(self):
		return {'val':self.val}
	
	def evaluate(self, q):
		if q == str(self.val):
			return self.val
		raise ActionMismatch
	
	def __repr__(self):
		return 'FixedAction({})'.format(repr(self.val))
	

	def __str__(self):
		return 'FixedAction({})'.format(str(self.val))
		
class ObjectAction(ActionElement, obj_type='obj'):
	def __init__(self, obj):
		self.obj = obj
		
	def __pack__(self):
		return {'obj': self.__class__._pack_obj(self.obj)}
	
	def __unpack__(self, data):
		ObjectAction.__init__(self, self.__class__._unpack_obj(data['obj']))
		
	def encode(self):
		return {'ID':self.obj._id, 'val':str(self.obj)}
	
	def evaluate(self, q):
		if q == self.obj._id:
			return self.obj
		raise ActionMismatch

class PlayerAction(ActionElement, obj_type='player'):
	def __init__(self, player):
		super().__init__()
		self.player = player
		
	def __pack__(self):
		return {'player': self.__class__._pack_obj(self.player)}
	
	def __unpack__(self, data):
		PlayerAction.__init__(self, self.__class__._unpack_obj(data['player']))
		
	def encode(self):
		return {'val':str(self.player)}
	
	def evaluate(self, q):
		if q == self.player.name:
			return self.player
		raise ActionMismatch

class TextAction(ActionElement, obj_type='text'): # allows player to enter arbitrary text as action
	
	def __init__(self):
		super().__init__()
		
	def __pack__(self):
		pack = self.__class__._pack_obj
		raise NotImplementedError
		
	def __unpack__(self, data):
		unpack = self.__class__._unpack_obj
		raise NotImplementedError
	
	def encode(self):
		raise NotImplementedError # TODO
	
	def evaluate(self, q):
		raise NotImplementedError # TODO
	

class NumberAction(ActionElement, obj_type='number'): # allows player to choose from a number (float/int) range
	
	def __init__(self):
		super().__init__()
	
	def __pack__(self):
		pack = self.__class__._pack_obj
		raise NotImplementedError
	
	def __unpack__(self, data):
		unpack = self.__class__._unpack_obj
		raise NotImplementedError
	
	def encode(self):
		raise NotImplementedError  # TODO
	
	def evaluate(self, q):
		raise NotImplementedError  # TODO

