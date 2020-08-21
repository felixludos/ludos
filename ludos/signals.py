


_signal_registry = {}
def register_signal(cls):
	_signal_registry[cls.__name__] = cls
	

class Signal(Exception):
	def __init_subclass__(cls, **kwargs):
		register_signal(cls)
	
	def get_static_format(self):
		return {}
	
# Control flow Signals

class GameOver(Signal):
	'''
	Flag to be raised anywhere in a GamePhase or GameObject to end a game.
	'''
	pass

class PhaseComplete(Signal):
	'''
	Flag to be raised anywhere in a GamePhase or GameObject to end phase and move on to the next one in the GameStack.
	'''
	def __init__(self, transfer=False): # transfer action to next phase
		'''
		
		:param transfer: if true then the current action will be sent to the next phase (default: False)
		'''
		super().__init__()
		self.transfer = transfer
		
	def transfer_action(self):
		'''
		Says whether the action should be transferred
		:return: bool whether or not the action should be sent to the next phase
		'''
		return self.transfer


class _PhaseControl(Signal): # possibly can include an action and player
	'''
	Signal used by game controller to transition to a different phase.
	
	WARNING: This signal should not be raised directly - use `SubPhase` or `SwitchPhase` instead.
	'''
	def __init__(self, phase, send_action=False, **kwargs):
		'''
		
		:param phase: name of a registered phase or an instance of a registered phase to switch to
		:type phase: str or GamePhase
		:param send_action: Pass current action into the new phase
		:type: send_action: bool
		:param kwargs: optional kwargs to be passed into new phase if it is just the name of a phase
		:type kwargs: any other keyword arguments
		'''
		super().__init__()
		self.phase = phase
		self.send_action = send_action
		self.kwargs = kwargs
		
	def transfer_action(self):
		'''
		
		:return: flag whether the action should be copied to the new phase
		:rtype: bool
		'''
		return self.send_action
		
	def stacks(self):
		'''

		:return: flag whether the current phase should be added back to the stack before beingging the new phase
		:rtype: bool
		'''
		raise NotImplementedError
		
	def get_phase(self):
		'''
		
		:return: new phase to switch to
		'''
		return self.phase
	
	def get_phase_kwargs(self):
		'''
		
		:return: keyword arguments for new phase (only used if it must be created)
		'''
		return self.kwargs


class SwitchPhase(_PhaseControl):
	'''
	Flag to be raised anywhere in a GamePhase or GameObject to switch the current phase,
	without returning to this phase afterwards.
	'''
	def stacks(self):
		return False
	
	
class SubPhase(_PhaseControl):
	'''
	Flag to be raised anywhere in a GamePhase or GameObject to transition to a different phase and then return back to
	the current one after that one is complete.
	'''
	def stacks(self):
		return True






