


class ClosedRegistryError(Exception):
	pass

class GameOver(Exception):
	pass

class PhaseComplete(Exception):
	pass

class PhaseInterrupt(Exception): # possibly can include an action and player
	def __init__(self, phase):
		super().__init__()
		self.phase = phase
		
	def get_phase(self):
		return self.phase

class MissingType(Exception):
	def __init__(self, obj, *typs):
		super().__init__('Before loading {} you must register: {}'.format(obj.__class__.__name__, ', '.join(typs)))

