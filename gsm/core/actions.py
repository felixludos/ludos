# import json
from ..containers import tdict, tset, tlist
from .object import GameObject
from ..mixins import Typed
from ..util import jsonify

def process_actions(raw): # getting a raw encoded set in, outputting a set ready to be jsonified
	
	if isinstance(raw, GameObject):
		return tdict(type='ID', val=raw._id)
	
	# handling complex action types (text entry, numbers...)
	if isinstance(raw, ActionQuery):
		return tdict(type=raw.get_type(), val=raw.encode())
	
	if isinstance(raw, tuple):
		return tuple(process_actions(r) for r in raw)
	if isinstance(raw, tset):
		return tset(process_actions(r) for r in raw)
	
	return tdict(type='fixed', val=str(raw))
	


class GameActions(object): # created and returned in phases
	
	def __init__(self):
		self.reset()
	
	def reset(self):
		# actions
		self.options = []
		self.status = None
		
		# info
		self.info = tdict()
	
	def save_options(self, actions, desc=None): # each action group/option can have its own description
		option = tdict(actions=actions)
		if desc is not None:
			option.desc = desc
		self.options.append(option)
	
	def set_status(self, status): # these instructions are global, for all action groups/options
		self.status = status
	
	def verify(self, action):
		raise NotImplementedError # TODO
	
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
		
		options = tdict(actions=self.options)
		
		if self.status is not None:
			options.status = str(self.status)
			
		options.info = self.info
		
		return jsonify(options)


# Advanced action queries

class InvalidAction(Exception):
	def __init__(self, action):
		super().__init__('{} is an invalid action'.format(str(action)))

class ActionQuery(Typed):
	
	def encode(self):
		raise NotImplementedError
	
	def evaluate(self, q):
		raise NotImplementedError

class TextAction(ActionQuery): # allows player to enter arbitrary text as action
	
	def __init__(self):
		super().__init__('text')
	
	def encode(self):
		raise NotImplementedError # TODO
	
	def evaluate(self, q):
		raise NotImplementedError # TODO
	

class NumberAction(ActionQuery): # allows player to choose from a number (float/int) range
	
	def __init__(self):
		super().__init__('number')
	
	def encode(self):
		raise NotImplementedError  # TODO
	
	def evaluate(self, q):
		raise NotImplementedError  # TODO

