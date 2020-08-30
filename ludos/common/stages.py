
import inspect

from .. import gdict, glist, gset
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
	_stage_registry = gdict()
	_decision_registry = gdict()
	_entry_stage_name = None
	
	def __init_subclass__(cls, **kwargs):
		
		super().__init_subclass__(**kwargs)
		
		parents = cls.__mro__
		parent = parents[1] if issubclass(parents[1], StagePhase) else StagePhase
		
		preg = parent.__dict__['_stage_registry']
		if '_stage_registry' not in cls.__dict__:
			reg = gdict()
			cls._stage_registry = reg
		else:
			reg = cls.__dict__['_stage_registry']
		for name, info in preg.items():
			if name not in reg:
				cls.register_stage(name, **info)
		
		preg = parent.__dict__['_decision_registry']
		if '_decision_registry' not in cls.__dict__:
			reg = gdict()
			cls._decision_registry = reg
		else:
			reg = cls.__dict__['_decision_registry']
		for name, info in preg.items():
			if name not in reg:
				cls.register_decision(name, **info)

		pentry = parent.__dict__['_entry_stage_name']
		entry = cls.__dict__['_entry_stage_name'] if '_entry_stage_name' in cls.__dict__ else None
		if pentry is not None and entry is None:
			cls._entry_stage_name = pentry
			

	@classmethod
	def register_stage(cls, name, fn, entry=False, switch=None, decide=None):
		
		if '_stage_registry' not in cls.__dict__:
			reg = gdict()
			cls._stage_registry = reg
		else:
			reg = cls.__dict__['_stage_registry']
		
		if name in reg:
			prt.warning(f'A stage called {name} was already registered in phase {cls.name}')
		
		reg[name] = {'fn': fn, 'switch': switch, 'decide': decide}
		
		if entry:
			cls._entry_stage_name = name
	
	@classmethod
	def register_decision(cls, name, fn, action_groups=None):
		
		if '_decision_registry' not in cls.__dict__:
			reg = gdict()
			cls._decision_registry = reg
		else:
			reg = cls.__dict__['_decision_registry']
		
		if name in reg:
			prt.warning(f'A decision called {name} was already registered in phase {cls.name}')
		
		reg[name] = {'fn': fn, 'action_groups': action_groups}
		
	@classmethod
	def get_stage(cls, name):
		if name not in cls._stage_registry:
			raise NotFoundException('stage', name, cls.name)
		return cls._stage_registry[name]['fn']

	@classmethod
	def get_decision(cls, name):
		if name not in cls._decision_registry:
			raise NotFoundException('decision', name, cls.name)
		return cls._decision_registry[name]['fn']
	
	@classmethod
	def get_entry_stage(cls):
		if cls._entry_stage_name is None:
			raise NoEntryStageException(cls)
		return cls._entry_stage_name
	
	@classmethod
	def get_stage_info(cls, name):
		if name not in cls._stage_info:
			raise NotFoundException('stage', name, cls.name)
		return cls._stage_info[name]
	
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

class FixedStagePhase(StagePhase):
	@classmethod
	def update_current_stage(cls, stage_name, decision_name):
		pass
	

def Stage(name=None, switch=None, decide=None,):

	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
	
		def __set_name__(self, phase, fn_name):
			
			nonlocal name, switch, decide
			
			# register stage
			if name is None:
				name = fn_name
			
			phase.register_stage(name, self.fn, switch=switch, decide=decide)
			
			setattr(phase, fn_name, self.fn)

	return _reg


def Entry_Stage(name=None, switch=None, decide=None,):
	class _reg(object):
		def __init__(self, fn):
			self.fn = fn
		
		def __set_name__(self, phase, fn_name):
			nonlocal name
			
			# register stage
			if name is None:
				name = fn_name
			
			phase.register_stage(name, self.fn, entry=True, switch=switch, decide=decide)
			
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
				
			phase.register_decision(name, self.fn, action_groups=action_groups)
			
			setattr(phase, fn_name, self.fn)
	
	return _reg


