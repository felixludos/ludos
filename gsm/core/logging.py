
from ..basic_containers import tdict, tlist, tset
from .object import GameObject

from ..mixins import Named, Typed, Savable, Transactionable
from ..util import Player
from string import Formatter

'''
log formatting:
- players
- game objects
- structure - print to different levels (increment or reset)
'''

class GameLogger(Savable, Transactionable):
	def __init__(self, players=[], indents=True, debug=False):
		super().__init__()
		self.logs = tdict({p: tlist() for p in players})
		self.recent = tdict({p: tlist() for p in players})
		self.debug = debug
		
		self.level = 0 if indents else None
		
		self._in_transactions = False
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		data['logs'] = pack(self.logs)
		data['recent'] = pack(self.recent)
		data['debug'] = pack(self.debug)
		data['level'] = pack(self.level)
		
		return data
	
	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		
		self = cls()
		
		self.logs = unpack(data['logs'])
		self.recent = unpack(data['recent'])
		self.debug = unpack(data['debug'])
		self.level = unpack(data['level'])
	
		return self
	
	def begin(self):
		if self.in_transaction():
			self.commit()
		
		self._in_transactions = True
		self.logs.begin()
		self.recent.begin()
	
	def in_transaction(self):
		return self._in_transactions
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._in_transactions = False
		self.logs.commit()
		self.recent.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transactions = False
		self.logs.abort()
		self.recent.abort()
	
	def update_all(self, objs, player=None):
		if player is not None:
			self.recent[player].extend(objs)
			self.logs[player].extend(objs)
			return
		for update, log in zip(self.recent.values(), self.logs.values()):
			update.extend(objs)
			log.extend(objs)
	
	
	def _log(self, obj, player=None):
		
		if player is not None:
			self.logs[player].append(obj)
			self.recent[player].append(obj)
		else:
			for log, recent in zip(self.logs.values(), self.recent.values()):
				log.append(obj)
				recent.append(obj)
	
	def pull(self, player):
		log = self.recent[player].copy()
		self.recent[player].clear()
		return log
	
	def get_full(self, player=None):
		if player is not None:
			return self.logs[player].copy()
		return tdict({p: self.logs[p].copy() for p in self.logs})



# TODO: add formats for headings, lists, maybe images, ...
# TODO: make sure frontend can handle some basic/standard format instructions


# class OldGameLogger(Transactionable):
# 	def __init__(self, *players, stdout=False):
# 		self.stdout = stdout
# 		self.logs = adict({p :deque() for p in players})
# 		self.updates = adict({p :deque() for p in players})
# 		self.collectors = None
#
# 	def save_state(self):
# 		state = {
# 			'stdout': self.stdout,
# 			'logs': {k :list(v) for k ,v in self.logs.items()},
# 			'updates': {k :list(v) for k ,v in self.updates.items()},
# 		}
# 		if self.collectors is not None:
# 			state['collectors'] = {k :list(v) for k ,v in self.collectors.items()}
# 		return state
#
# 	def load_state(self, data):
# 		self.stdout = data['stdout']
# 		self.logs = adict(data['logs'])
# 		self.updates = adict(data['updates'])
# 		if 'collectors' in data:
# 			self.collectors = adict(data['collectors'])
#
# 	def begin(self):
# 		if self.in_transaction():
# 			self.abort()
# 		self.collectors = adict({p :deque() for p in self.updates.keys()})
#
# 	def in_transaction(self):
# 		return self.collectors is not None
#
# 	def commit(self):
# 		if not self.in_transaction():
# 			return
# 		collectors = self.collectors
# 		self.collectors = None
# 		for p, objs in collectors.items():
# 			self.update_all(objs, player=p)
#
# 	def abort(self):
# 		if not self.in_transaction():
# 			return
# 		self.collectors = None
#
# 	def update_all(self, objs, player=None):
# 		if player is not None:
# 			self.updates[player].extend(objs)
# 			self.logs[player].extend(objs)
# 			return
# 		for update, log in zip(self.updates.values(), self.logs.values()):
# 			update.extend(objs)
# 			log.extend(objs)
#
# 	def write(self, obj, end='\n', player=None):
# 		obj += end
# 		if self.in_transaction():
# 			if player is None:
# 				for collector in self.collectors.values():
# 					collector.append(obj)
# 				return
# 			return self.collectors[player].append(obj)
# 		self.update(obj, player=player)
# 		if self.stdout:
# 			print(obj, end='')
#
# 	def update(self, obj, player=None):
#
# 		if player is not None:
# 			self.updates[player].append(obj)
# 			self.logs[player].append(obj)
# 			return
# 		for update, log in zip(self.updates.values(), self.logs.values()):
# 			update.append(obj)
# 			log.append(obj)
#
# 	def pull(self, player):
# 		log = ''.join(self.updates[player])
# 		self.updates[player].clear()
# 		return log
#
# 	def get_full(self, player=None):
# 		if player is not None:
# 			return ''.join(self.logs[player])
# 		return adict({p :''.join(self.logs[p]) for p in self.logs})