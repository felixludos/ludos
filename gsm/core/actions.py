# import json
from itertools import product, chain
from ..basic_containers import tdict, tset, tlist
from .object import obj_jsonify, GameObject
from ..mixins import Typed, Named, Transactionable, Savable, Pullable
from ..signals import ActionMismatch, UnknownActionElement, InvalidActionError
from ..writing import RichWriter
# from ..util import jsonify


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



class GameActions(Transactionable, Savable, Pullable): # created and returned in phases
	
	def __init__(self):
		super().__init__()
		self._current = None
		self._desc = RichWriter(end='')
		self._options = tlist()
		
		self.status = RichWriter(end='') # should be accessed directly by dev
		self.info = tdict() # should be accessed directly by dev
	
	def in_transaction(self):
		return self._current is not None
	
	def begin(self):
		if self.in_transaction():
			return
		
		self._current = tset()
		self._desc.clear()

	def commit(self):
		if not self.in_transaction():
			return

		opt = tdict(actions=process_actions(self._current))
		if len(self._desc):
			opt.desc = self._desc.pull()
		self._options.append(opt)
		
		self._current = None

	def abort(self):
		if not self.in_transaction():
			return

		self._current = None
	
	def __enter__(self):
		# self._context = True
		self.begin()

	def __exit__(self, type, *args):
		# self._context = False
		if type is None:
			self.commit()
		else:
			self.abort()
		return None if type is None else type.__name__ == 'AbortTransaction'
		
	def write(self, *args, **kwargs):
		self._desc.write(*args, **kwargs)
	def writef(self, *args, **kwargs):
		self._desc.writef(*args, **kwargs)
	
	def __getattribute__(self, item):
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._current.__getattribute__(item)
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['_current'] = pack(self._current)
		data['_desc'] = pack(self._desc)
		data['_options'] = pack(self._options)
		data['status'] = pack(self.status)
		data['info'] = pack(self.info)
		
		return data
	
	@classmethod
	def __load(cls, data):
		self = cls()
		unpack = cls.__unpack
		
		self._current = unpack(data['_current'])
		self._desc = unpack(data['_desc'])
		self._options = unpack(data['options'])
		self.status = unpack(data['status'])
		self.info = unpack(data['info'])
		
		return self
	
	def verify(self, action): # action should be a tuple
		
		for option in self._options:
			
			actionset = decode_action_set(option.actions)
			
			for tpl in actionset:
				if len(tpl) == len(action):
					try:
						out = tuple(elm.evaluate(a) for elm, a in zip(tpl, action))
					except ActionMismatch:
						pass # action didnt match
					else:
						return out
					
		raise InvalidActionError(action)
	
	def __len__(self):
		return len(self._options)
	
	def __add__(self, other):
		new = GameActions()
		new._options = self._options + other._options
		new.status.text = self.status.text + other.status.text
		return new
		
	def get_info(self):
		return self.info
	
	def pull(self): # returns jsonified obj
		
		options = []
		for opt in self._options:
			options.append({})
			options[-1]['actions'] = format_actions(opt.actions)
			if 'desc' in opt:
				options[-1]['desc'] = opt.desc
		
		out = {
			'options': options,
		}
		
		if len(self.status):
			out['status'] = self.status.pull()
			
		if len(self.info):
			out['info'] = obj_jsonify(self.info)
			
		return out


# Advanced action queries

class ActionElement(Typed, Transactionable, Savable):
	
	def encode(self):
		raise NotImplementedError
	
	def evaluate(self, q): # either returns element or raises ActionMismatch
		raise NotImplementedError

class FixedAction(ActionElement):
	def __init__(self, val): # works for primitives
		# super().__init__(type(val).__name__)
		super().__init__('fixed')
		self.val = val

	def __save(self):
		return self.val

	@classmethod
	def __load(cls, data):
		return cls(data)

	def encode(self):
		return {'val':self.val}
	
	def evaluate(self, q):
		if q == self.val:
			return self.val
		raise ActionMismatch
	
	def __repr__(self):
		return 'FixedAction({})'.format(repr(self.val))
	

	def __str__(self):
		return 'FixedAction({})'.format(str(self.val))
		
class ObjectAction(ActionElement):
	def __init__(self, obj):
		super().__init__('obj')
		self.obj = obj
		
	def __save(self):
		return {'obj': self.__class__.__pack(self.obj)}
	
	@classmethod
	def __load(cls, data):
		return cls(cls.__unpack(data['obj']))
		
	def encode(self):
		return {'ID':self.obj._id}
	
	def evaluate(self, q):
		if q == self.obj._id:
			return self.obj
		raise ActionMismatch

class TextAction(ActionElement): # allows player to enter arbitrary text as action
	
	def __init__(self):
		super().__init__('text')
		
	def __save(self):
		pack = self.__class__.__pack
		raise NotImplementedError
		
	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		raise NotImplementedError
	
	def encode(self):
		raise NotImplementedError # TODO
	
	def evaluate(self, q):
		raise NotImplementedError # TODO
	

class NumberAction(ActionElement): # allows player to choose from a number (float/int) range
	
	def __init__(self):
		super().__init__('number')
	
	def __save(self):
		pack = self.__class__.__pack
		raise NotImplementedError
	
	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		raise NotImplementedError
	
	def encode(self):
		raise NotImplementedError  # TODO
	
	def evaluate(self, q):
		raise NotImplementedError  # TODO

