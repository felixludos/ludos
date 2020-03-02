from ..mixins import Named, Transactionable, Packable
from humpack import tset, tdict, tlist, tstack, pack_member, unpack_member
from ..signals import PhaseComplete
from ..io.registry import register_phase

class GameStack(Transactionable, Packable):
	def __init__(self,):
		super().__init__()
		
		self._in_transaction = False
		self._stack = tstack()
		self._phases = tdict()
		self._start_phase = None
		
	def begin(self):
		if self.in_transaction():
			return
		self._in_transaction = True
		self._stack.begin()
		self._phases.begin()
		
	def in_transaction(self):
		return self._in_transaction
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self._stack.commit()
		self._phases.commit()
		
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self._stack.abort()
		self._phases.abort()
		
	def __pack__(self):
		
		data = {}
		
		data['_stack'] = pack_member(self._stack)
		data['_phases'] = pack_member(self._phases)
		data['_in_transaction'] = pack_member(self._in_transaction)
		data['_start'] = pack_member(self._start_phase)
		
		return data
	
	def __unpack__(self, data):
		
		GameStack.__init__(self)
		
		self._stack = unpack_member(data['_stack'])
		self._phases = unpack_member(data['_phases'])
		self._in_transaction = unpack_member(data['_in_transaction'])
		self._start_phase = unpack_member(data['_start'])
	
	
	def populate(self, phases):
		
		start_phase = None
		
		for name, info in phases.items():
			self._phases[name] = tdict(info)
			if 'start' in info and info['start']:
				start_phase = name
				
		if self._start_phase is None:
			assert start_phase is not None, 'no start phase found in: {}'.format(phases)
		
		self._start_phase = start_phase
		
	def create(self, name, **kwargs):
		
		cls = self._phases[name].cls
		if 'props' in self._phases[name]:
			props = self._phases[name].props
			props.update(kwargs)
			kwargs = props
			
		phase = cls(**kwargs)
		return phase
		
	# stack
	
	def __len__(self):
		return len(self._stack)
	
	def _process_entry(self, phase, **kwargs):
		if phase in self._phases:
			phase = self.create(phase, **kwargs)
		return phase
	
	def reset(self, ctrl):
		self._stack.clear()
		self.push(self._start_phase)
		
	def push(self, *items, **kwargs):
		for item in items:
			self._stack.push(self._process_entry(item, **kwargs))
	
	def extend(self, items, **kwargs):
		self._stack.extend(self._process_entry(item, **kwargs) for item in items)
	
	def pop(self):
		return self._stack.pop()
	
	def peek(self, n=0):
		return self._stack.peek(n)
	
	def __getitem__(self, item):
		return self._stack[item]


class GamePhase(Named, tdict):
	
	def __init_subclass__(cls, name=None, game=None, start=False, req_stack=None, **kwargs):
		super().__init_subclass__(**kwargs)
		
		if name is None:
			name = cls.__name__
		
		cls.name = name
		
		if req_stack is not None:
			cls._req_stack = req_stack
		
		if game is not None:
			register_phase(game, cls, name=name, start=start)
	
	@classmethod
	def get_name(cls): # TODO probably should use 'Typed' mixin here
		return cls.name
	
	def __init__(self, name=None, **info):
		if name is None:
			name = self.__class__.__name__
		super().__init__(name=name, **info)
	
	def execute(self, C, player=None, action=None): # must be implemented
		raise NotImplementedError
	
	def encode(self, C): # by default no actions are necessary
		raise PhaseComplete # this should usually return a GameActions instance
