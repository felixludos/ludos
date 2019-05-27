
from .structures import Transactionable, adict
from collections import deque

class Logger(Transactionable):
	def __init__(self, *players, stdout=False):
		self.stdout = stdout
		self.logs = adict({p :deque() for p in players})
		self.updates = adict({p :deque() for p in players})
		self.collectors = None
	
	def save_state(self):
		state = {
			'stdout': self.stdout,
			'logs': {k :list(v) for k ,v in self.logs.items()},
			'updates': {k :list(v) for k ,v in self.updates.items()},
		}
		if self.collectors is not None:
			state['collectors'] = {k :list(v) for k ,v in self.collectors.items()}
		return state
	
	def load_state(self, data):
		self.stdout = data['stdout']
		self.logs = adict(data['logs'])
		self.updates = adict(data['updates'])
		if 'collectors' in data:
			self.collectors = adict(data['collectors'])
	
	def begin(self):
		if self.in_transaction():
			self.abort()
		self.collectors = adict({p :deque() for p in self.updates.keys()})
	
	def in_transaction(self):
		return self.collectors is not None
	
	def commit(self):
		if not self.in_transaction():
			return
		collectors = self.collectors
		self.collectors = None
		for p, objs in collectors.items():
			self.update_all(objs, player=p)
	
	def abort(self):
		if not self.in_transaction():
			return
		self.collectors = None
	
	def update_all(self, objs, player=None):
		if player is not None:
			self.updates[player].extend(objs)
			self.logs[player].extend(objs)
			return
		for update, log in zip(self.updates.values(), self.logs.values()):
			update.extend(objs)
			log.extend(objs)
	
	def write(self, obj, end='\n', player=None):
		obj += end
		if self.in_transaction():
			if player is None:
				for collector in self.collectors.values():
					collector.append(obj)
				return
			return self.collectors[player].append(obj)
		self.update(obj, player=player)
		if self.stdout:
			print(obj, end='')
	
	def update(self, obj, player=None):
		
		if player is not None:
			self.updates[player].append(obj)
			self.logs[player].append(obj)
			return
		for update, log in zip(self.updates.values(), self.logs.values()):
			update.append(obj)
			log.append(obj)
	
	def pull(self, player):
		log = ''.join(self.updates[player])
		self.updates[player].clear()
		return log
	
	def get_full(self, player=None):
		if player is not None:
			return ''.join(self.logs[player])
		return adict({p :''.join(self.logs[p]) for p in self.logs})