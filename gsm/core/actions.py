# import json
from ..containers import tdict, tset, tlist
from .object import GameObject
from ..mixins import Typed

def jsonify_actions(obj):
	if isinstance(obj, (list, tlist)):
		return [jsonify_actions(o) for o in obj]
	if isinstance(obj, (dict, tdict)):
		return {jsonify_actions(k):jsonify_actions(v) for k,v in obj.items()}
	if isinstance(obj, tuple):
		return [jsonify_actions(o) for o in obj]
	if isinstance(obj, (set, tset)):
		return {'set': [jsonify_actions(o) for o in obj]}
	return obj

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
		self.options = []
		self.instr = None
	
	def save_options(self, actions, desc=None): # each action group/option can have its own description
		option = {'actions': actions}
		if desc is not None:
			option['desc'] = desc
		self.options.append(option)
	
	def set_instructions(self, instr): # these instructions are global, for all action groups/options
		self.instr = instr
	
	def __add__(self, other):
		new = GameActions()
		new.options = self.options + other.options
		new.instr = self.instr
		if self.instr is None:
			new.instr = other.instr
		return new
	
	def pull(self):
		if self.instr is None and len(self.options) == 1 and 'desc' in self.options[0]:
			self.instr = self.options[0]['desc']
			del self.options[0]['desc']
		
		options = {'options': jsonify_actions(self.options)}
		
		if self.instr is not None:
			options['instructions'] = str(self.instr)
			
		return options


# Advanced action queries

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

