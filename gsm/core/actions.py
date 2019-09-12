# import json
from ..containers import tdict, tset, tlist
from .object import GameObject
from ..mixins import Typed, Named
from ..util import jsonify
from ..signals import ActionMismatch, UnknownActionElement, InvalidAction
from ..viz import _decode_action_set

def process_actions(raw): # process input when saving new action set (mostly turn options into ActionElement instances)
	
	if isinstance(raw, tuple):
		return tuple(process_actions(r) for r in raw)
	if isinstance(raw, set):
		return tset(process_actions(r) for r in raw)
	
	if isinstance(raw, GameObject):
		return ObjectAction(raw)
	if type(raw).__module__ == 'numpy': # unwrap numpy types
		return process_actions(raw.item())
	if isinstance(raw, (str, int, float)):
		return FixedAction(raw)
	
	if isinstance(raw, ActionElement):
		return raw
	
	raise UnknownActionElement(raw)
	

def format_actions(raw): # format action sets to be sent to frontend (mostly encoding ActionElements)
	
	if isinstance(raw, tuple):
		return tuple(format_actions(r) for r in raw)
	if isinstance(raw, set):
		return tset(format_actions(r) for r in raw)
	
	if isinstance(raw, ActionElement):
		info = tdict(raw.encode())
		info.type = raw.get_type()
		return info
		
	# all leaf elements must be ActionElement instances
	
	raise UnknownActionElement(raw)

class GameActions(tdict): # created and returned in phases
	
	def __init__(self):
		super().__init__()
		self.reset()
	
	def reset(self):
		# actions
		self.options = tlist()
		self.status = None
		
		# info
		self.info = tdict()
	
	def save_options(self, actions, desc=None): # each action group/option can have its own description
		option = tdict(actions=process_actions(actions))
		if desc is not None:
			option.desc = desc
		self.options.append(option)
	
	def set_status(self, status): # these instructions are global, for all action groups/options
		self.status = status
	
	def verify(self, action): # action should be a tuple
		
		for option in self.options:
			
			actionset = _decode_action_set(option.actions)
			
			for tpl in actionset:
				if len(tpl) == len(action):
					try:
						out = (elm.evaluate(a) for elm, a in zip(tpl, action))
					except ActionMismatch:
						pass
					else:
						return out
					
		raise InvalidAction(action)
	
	def __len__(self):
		return len(self.options)
	
	def __add__(self, other):
		new = GameActions()
		new.options = self.options + other.options
		new.status = self.status
		if self.status is None:
			new.status = other.status
		return new
	
	def get_info(self):
		return self.info
	
	def pull(self): # returns jsonified obj
		if self.status is None and len(self.options) == 1 and 'desc' in self.options[0]:
			self.status = self.options[0]['desc']
			del self.options[0]['desc']
		
		full = tdict(options=tlist())
		
		for opts in self.options:
			opts = opts.copy()
			opts.actions = format_actions(opts.actions)
			full.options.append(opts)
		
		if self.status is not None:
			full.status = str(self.status)
			
		full.info = self.info
		
		return jsonify(full)


# Advanced action queries


class ActionElement(Typed, tdict):
	
	def encode(self):
		raise NotImplementedError
	
	def evaluate(self, q): # either returns element or raises ActionMismatch
		raise NotImplementedError

class FixedAction(ActionElement):
	def __init__(self, val): # works for str, int, float
		super().__init__(type(val).__name__)
		self.conv = type(val) # from string to type
		self.val = val

	def encode(self):
		return tdict(val=str(self.val))
	
	def evaluate(self, q):
		if self.conv is not None:
			try:
				q = self.conv(q)
			except ValueError:
				raise ActionMismatch
		if q == self.val:
			return self.val
		raise ActionMismatch
		
class ObjectAction(ActionElement):
	def __init__(self, obj):
		super().__init__('obj')
		self.obj = obj
		
	def encode(self):
		return tdict(ID=self.obj._id)
	
	def evaluate(self, q):
		try:
			q = type(self.obj._id)(q)
		except ValueError:
			raise ActionMismatch
		if q == self.obj._id:
			return self.obj
		raise ActionMismatch

class TextAction(ActionElement): # allows player to enter arbitrary text as action
	
	def __init__(self):
		super().__init__('text')
	
	def encode(self):
		raise NotImplementedError # TODO
	
	def evaluate(self, q):
		raise NotImplementedError # TODO
	

class NumberAction(ActionElement): # allows player to choose from a number (float/int) range
	
	def __init__(self):
		super().__init__('number')
	
	def encode(self):
		raise NotImplementedError  # TODO
	
	def evaluate(self, q):
		raise NotImplementedError  # TODO

