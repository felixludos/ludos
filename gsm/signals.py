




# Control flow Exceptions

class GameOver(Exception):
	pass

class PhaseComplete(Exception):
	pass

class PhaseInterrupt(Exception): # possibly can include an action and player
	def __init__(self, phase, stack=True):
		super().__init__()
		self.phase = phase
		self.stack = stack
		
	def stacks(self):
		return self.stack
		
	def get_phase(self):
		return self.phase

# Controller registry errors

class ClosedRegistryError(Exception):
	pass

class MissingTypeError(Exception):
	def __init__(self, obj, *typs):
		super().__init__('Before loading {} you must register: {}'.format(obj.__class__.__name__, ', '.join(typs)))

class MissingObjectError(Exception):
	def __init__(self, name):
		super().__init__('{} is not a recognized GameObject type, have you registered it?'.format(name))

class MissingValueError(Exception):
	def __init__(self, typ, missing, *reqs):
		super().__init__('{} is missing {}, requires a value for: {}'.format(typ, missing, ', '.join(reqs)))
		
# action errors
		
class InvalidAction(Exception):
	def __init__(self, action):
		super().__init__('{} is an invalid action'.format(str(action)))
		
class ActionMismatch(Exception):
	pass

class UnknownActionElement(Exception):
	def __init__(self, obj):
		super().__init__('Unknown action element: {}, type: {}'.format(str(obj), type(obj)))
		self.obj = obj

# mixin errors

class UnregisteredClassError(Exception):
	def __init__(self, name):
		super().__init__('"{}" is not registered (does it subclass Savable?)'.format(name))

class LoadInitFailureError(Exception):
	def __init__(self, obj_type):
		super().__init__('An instance of {obj_type} was unable to load (make sure {obj_type}.__init__ doesnt have any required arguments)'.format(obj_type=obj_type))
