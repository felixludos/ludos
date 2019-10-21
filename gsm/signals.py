


# general

class UnknownElementError(Exception):
	def __init__(self, obj):
		super().__init__('Cannot un/jsonify {}: {}'.format(type(obj), obj))

# Control flow Exceptions

class GameOver(Exception):
	pass

class PhaseComplete(Exception):
	def __init__(self, transfer=False): # transfer action to next phase
		super().__init__()
		self.transfer = transfer
		
	def transfer_action(self):
		return self.transfer

class SwitchPhase(Exception): # possibly can include an action and player
	def __init__(self, phase, stack=True, send_action=False, **kwargs):
		super().__init__()
		self.phase = phase
		self.stack = stack
		self.send_action = send_action
		self.kwargs = kwargs
		
	def transfer_action(self):
		return self.send_action
		
	def stacks(self):
		return self.stack
		
	def get_phase(self):
		return self.phase
	
	def get_phase_kwargs(self):
		return self.kwargs

# Controller errors

class InvalidKeyError(Exception):
	pass

class InvalidPlayerError(Exception):
	def __init__(self, player):
		super().__init__('Invalid player: {}'.format(player))

# Controller registry errors

class ClosedRegistryError(Exception):
	pass

class RegistryCollisionError(Exception):
	def __init__(self, key):
		super().__init__('The key {} has already been registered'.format(key))

class MissingTypeError(Exception):
	def __init__(self, obj, *typs):
		super().__init__('Before loading {} you must register: {}'.format(obj.__class__.__name__, ', '.join(typs)))

class MissingObjectError(Exception):
	def __init__(self, name):
		super().__init__('{} is not a recognized GameObject type, have you registered it?'.format(name))

class NoActiveGameError(Exception):
	pass

# host errors

class InvalidValueError(Exception):
	pass

class UnknownUserError(Exception):
	pass
class UnknownPlayerError(Exception):
	pass

class UnknownGameError(Exception):
	pass
class UnknownInterfaceError(Exception):
	pass

class LoadConsistencyError(Exception):
	pass

# action errors
		
class InvalidActionError(Exception):
	def __init__(self, action):
		super().__init__('{} is an invalid action'.format(str(action)))
		
class ActionMismatch(Exception):
	pass

class UnknownActionElement(Exception):
	def __init__(self, obj):
		super().__init__('Unknown action element: {}, type: {}'.format(str(obj), type(obj)))
		self.obj = obj

# object errors

class InvalidInitializationError(Exception):
	def __init__(self):
		super().__init__('All GameObjects Must be created through the GameTable.create')

class MissingValueError(Exception):
	def __init__(self, typ, missing, *reqs):
		super().__init__('{} is missing {}, requires a value for: {}'.format(typ, missing, ', '.join(reqs)))


# game table errors

class ObjectIDCollisionError(Exception):
	def __init__(self, ID):
		super().__init__('A GameObject with ID {} already exists'.format(ID))

# class ZombieObjectException(Exception): # gets thrown when a SETTER is called from a GameObject even after it was removed from the game table
# 	def __init__(self, obj):
# 		super().__init__('{} has already beem removed from the GameTable'.format(repr(obj)))

# logging

class FormatException(Exception):
	pass


