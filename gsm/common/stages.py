
import inspect

from .. import tdict, tlist, tset
from ..mixins import Named
from ..core import GamePhase
from ..util import get_printer
from ..signals import PhaseComplete

prt = get_printer(__name__)

class NoEntryStageException(Exception):
	def __init__(self, cls):
		super().__init__(f'{cls.name} has no registered entry stage')

class NotFoundException(Exception):
	def __init__(self, type, name, loc):
		super().__init__(f'{type} {name} was not found in {loc}')

class Switch(Exception):
	def __init__(self, name, send_action=False, **info):
		self.name = name
		self.send_action = send_action
		self.info = info

class Decide(Exception):
	def __init__(self, name, **info):
		self.name = name
		self.info = info

class StagePhase(GamePhase):
	
	def __init_subclass__(cls, **kwargs):
		
		super().__init_subclass__(**kwargs)
		
		cls.stages = tdict()
		cls.entry_stage = None
		cls.decisions = tdict()
		cls.decision_action_groups = tdict()
		
	@classmethod
	def get_stage(cls, name):
		if name not in cls.stages:
			raise NotFoundException('stage', name, cls.name)
		return cls.stages[name]

	@classmethod
	def get_decision(cls, name):
		if name not in cls.decisions:
			raise NotFoundException('decision', name, cls.name)
		return cls.deicisions[name]
	
	@classmethod
	def get_entry_stage(cls):
		if cls.entry_stage is None:
			raise NoEntryStageException(cls)
		return cls.entry_stage
		
	def __init__(self, *args, current_stage_policy='latest', **kwargs):
		super().__init__(*args, **kwargs)
		
		assert current_stage_policy in {'entry', 'latest'}, f'unknown current stage policy: {current_stage_policy}'
		
		self.current_stage_policy = current_stage_policy
		self.current_stage = self.get_entry_stage()
		self.decision_info = None
		
	def set_current_stage(self, name):
		self.current_stage = self.get_stage(name)
		
	def execute(self, C, player=None, action=None):
		stage = self.get_stage(self.current_stage)
		self.decision_info = None
		
		stage_info = {}
		
		while self.decision_info is None:
			try:
				stage(C, player=player, action=action, **stage_info)
			except Switch as s:
				stage = self.get_stage(s.name)
				stage_info = s.info
				if not s.send_action:
					action = None
				if self.current_stage_policy == 'latest':
					self.current_stage = s.name
			except Decide as d:
				self.decision_info = d.name, d.info
			else:
				break
	
	def encode(self, C):
		
		if self.decision_info is None:
			raise PhaseComplete
		
		name, info = self.decision_info
		
		decision = self.get_decision(name)
		out = decision(C, **info)
		
		self.decision_info = None
		return out
	
def Stage(name=None):

	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
	
		def __set_name__(self, phase, fn_name):
			
			nonlocal name
			
			# register stage
			if name is None:
				name = fn_name
			
			if name in phase.stages:
				prt.warning(f'A stage called {name} was already registered in phase {phase.name}')
				
			phase.stages[name] = self.fn
			
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
			
			if name in phase.stages:
				prt.warning(f'A stage called {name} was already registered in phase {phase.name}')
			
			phase.stages[name] = self.fn
			
			if phase.entry_stage is not None:
				prt.warning(f'{phase.name} already has an entry stage, now setting to {name}')
				
			phase.entry_stage = name
			
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
			
			if name in phase.stages:
				prt.warning(f'A stage called {name} was already registered in phase {phase.name}')
			
			phase.decisions[name] = self.fn
			
			if action_groups is not None:
				if name not in phase.decision_action_groups:
					phase.decision_action_groups[name] = tset()
				phase.decision_action_groups[name].update(action_groups)
			else:
				prt.info(f'No action groups provided for decision {name} in {phase.name}')
			
			setattr(phase, fn_name, self.fn)
	
	return _reg


