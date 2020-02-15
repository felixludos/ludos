from ..mixins import Named, Transactionable, Packable
from humpack import tset, tdict, tlist, tstack
from ..signals import PhaseComplete

class GameStack(Transactionable, Packable):
	def __init__(self):
		super().__init__()
		
		self._in_transaction = False
		self._stack = tstack()
		self._phases = tdict()
		
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
		pack = self.__class__._pack_obj
		
		data = {}
		
		data['_stack'] = pack(self._stack)
		data['_phases'] = pack(self._phases)
		data['_in_transaction'] = pack(self._in_transaction)
		
		return data
	
	def __unpack__(self, data):
		unpack = self.__class__._unpack_obj
		
		GameStack.__init__(self)
		
		self._stack = unpack(data['_stack'])
		self._phases = unpack(data['_phases'])
		self._in_transaction = unpack(data['_in_transaction'])
	
	# registry
	
	def register(self, cls, name=None, **props):
		if name is None:
			name = cls.__class__.__name__
		self._phases[name] = tdict(phase_cls=cls, props=props)
		
	def create(self, name, **kwargs):
		
		cls = self._phases[name].phase_cls
		props = self._phases[name].props
		props.update(kwargs)
		
		phase = cls(**props)
		phase.name = name
		return phase
		
	# stack
	
	def __len__(self):
		return len(self._stack)
	
	def reset(self, phases=None, **kwargs):
		self._stack.clear()
		if phases is not None:
			self.extend(phases, **kwargs)
		
	def _process_entry(self, item, **kwargs):
		if item in self._phases:
			return self.create(item, **kwargs)
		return item
		
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
	
	def __init__(self, name=None, **info):
		if name is None:
			name = self.__class__.__name__
		super().__init__(name=name, **info)
	
	def execute(self, C, player=None, action=None): # must be implemented
		raise NotImplementedError
	
	def encode(self, C): # by default no actions are necessary
		raise PhaseComplete # this should usually return a GameActions instance
