
import inspect

from .. import tdict, tlist, tset
from ..mixins import Named
from ..core import GamePhase
from ..util import get_printer
from ..signals import PhaseComplete, Signal
from ..errors import GameError

prt = get_printer(__name__)

class NoEntryStageException(Exception):
	def __init__(self, cls):
		super().__init__(f'{cls.name} has no registered entry stage')

class NotFoundException(Exception):
	def __init__(self, type, name, loc):
		super().__init__(f'{type} {name} was not found in {loc}')

class Switch(Signal):
	def __init__(self, name, send_action=False, **info):
		self.name = name
		self.send_action = send_action
		self.info = info

class Decide(Signal):
	def __init__(self, name, **info):
		self.name = name
		self.info = info

class StagePhase(GamePhase):
	
	def __init_subclass__(cls, **kwargs):
		
		super().__init_subclass__(**kwargs)
		
		cls._stage_registry = StagePhase._stage_registry
		# cls._entry_stage_name = StagePhase._entry_stage_name
		cls._decision_registry = StagePhase._decision_registry
		cls._decision_action_groups = StagePhase._decision_action_groups
		
		StagePhase._clear_stages()
		
	@classmethod
	def _clear_stages(cls):
		cls._stage_registry = tdict()
		cls._entry_stage_name = None
		cls._decision_registry = tdict()
		cls._decision_action_groups = tdict()
		
	@classmethod
	def get_stage(cls, name):
		if name not in cls._stage_registry:
			raise NotFoundException('stage', name, cls.name)
		return cls._stage_registry[name]

	@classmethod
	def get_decision(cls, name):
		if name not in cls._decision_registry:
			raise NotFoundException('decision', name, cls.name)
		return cls._decision_registry[name]
	
	@classmethod
	def get_entry_stage(cls):
		if cls._entry_stage_name is None:
			raise NoEntryStageException(cls)
		return cls._entry_stage_name
	
	@classmethod
	def _get_static_stage_format(cls):
		return {}
	
	@classmethod
	def _get_static_decision_format(cls):
		return {}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.current_stage = self.get_entry_stage()
		self.decision_info = None
		
	def set_current_stage(self, stage_name):
		self.current_stage = stage_name
	
	def update_current_stage(self, stage_name, decision_name):
		self.set_current_stage(stage_name)
		
	def execute(self, C, player=None, action=None):
		stage_name = self.current_stage
		self.decision_info = None
		
		stage_info = {}
		
		while self.decision_info is None:
			try:
				stage = self.get_stage(stage_name)
				stage(self, C, player=player, action=action, **stage_info)
			except Switch as s:
				stage_name = s.name
				stage_info = s.info
				if not s.send_action:
					action = None
			except Decide as d:
				self.update_current_stage(stage_name, d.name)
				self.decision_info = d.name, d.info
			else:
				raise GameError(f'{stage_name} ended without raising a signal')
	
	def encode(self, C):
		
		if self.decision_info is None:
			raise PhaseComplete
		
		name, info = self.decision_info
		
		decision = self.get_decision(name)
		out = decision(self, C, **info)
		
		self.decision_info = None
		return out
	
StagePhase._clear_stages() # prepare registries

class FixedStagePhase(StagePhase):
	@classmethod
	def update_current_stage(cls, stage_name, decision_name):
		pass
	

def Stage(name=None):

	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
	
		def __set_name__(self, phase, fn_name):
			
			nonlocal name
			
			# register stage
			if name is None:
				name = fn_name
			
			if name in phase._stage_registry:
				prt.warning(f'A stage called {name} was already registered in phase {phase.name}')
				
			phase._stage_registry[name] = self.fn
			
			setattr(phase, fn_name, self.fn)

	return _reg


def Entry_Stage(name=None):
	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
		
		def __set_name__(self, phase, fn_name):
			nonlocal name
			
			# register stage
			if name is None:
				name = fn_name
			
			if name in phase._stage_registry:
				prt.warning(f'A stage called {name} was already registered in phase {phase.name}')
			
			phase._stage_registry[name] = self.fn
			
			if phase._entry_stage_name is not None:
				prt.warning(f'{phase.name} already has an entry stage, now setting to {name}')
			
			phase._entry_stage_name = name
			
			setattr(phase, fn_name, self.fn)
			
	return _reg


def Decision(name=None, action_groups=None):
	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
		
		def __set_name__(self, phase, fn_name):
			
			nonlocal name, action_groups
			
			if name is None:
				name = fn_name
			
			if name in phase._decision_registry:
				prt.warning(f'A decision called {name} was already registered in phase {phase.name}')
			
			phase._decision_registry[name] = self.fn
			
			if action_groups is not None:
				if name not in phase._decision_action_groups:
					phase._decision_action_groups[name] = tset()
				phase._decision_action_groups[name].update(action_groups)
			else:
				prt.info(f'No action groups provided for decision {name} in {phase.name}')
			
			setattr(phase, fn_name, self.fn)
	
	return _reg


