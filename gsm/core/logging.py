
from humpack import tset, tdict, tlist
from .object import GameObject
from ..writing import RichWriter, LogWriter
from ..mixins import Named, Typed, Savable, Transactionable
# from ..util import Player
from string import Formatter

'''
log formatting:
- players
- game objects
- structure - print to different levels (increment or reset)
'''

class GameLogger(LogWriter):
		
	def reset(self, players):
		self.writers = tdict({p: LogWriter(indent_level=self.indent_level, debug=self.debug)
		                      for p in players})
		
		super().reset()
		
	def __save__(self):
		data = super().__save__()
		data['writers'] =  self.__class__._pack_obj(self.writers)
		return data
	
	def __load__(self, data):
		super().__load__(data)
		self.writers = self.__class__._unpack_obj(data['writers'])
	
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
		
		super().begin()
		self.writers.begin()
	
	def commit(self):
		if not self.in_transaction():
			return
		
		super().commit()
		self.writers.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		
		super().abort()
		self.writers.abort()
	
	def __getitem__(self, item):
		return self.writers[item]
	
	def zindent(self):  # reset indent
		super().zindent()
		for log in self.writers.values():
			log.zindent()
	
	def iindent(self, n=1):  # increment indent
		super().iindent(n)
		for log in self.writers.values():
			log.iindent(n)
	
	def dindent(self, n=1):  # decrement indent
		super().dindent(n)
		for log in self.writers.values():
			log.dindent(n)
	
	def write(self, *args, **kwargs):
		
		super().write(*args, **kwargs)
		
		for log in self.writers.values():
			log.extend(self.text[-1])
	
	def writef(self, *args, **kwargs):
		
		super().writef(*args, **kwargs)
		
		for log in self.writers.values():
			log.extend(self.text[-1])
	
	def pull(self, player=None):
		if player is None:
			update = self.get_log()
		else:
			update = self.writers[player].pull()
			self.writers[player].text.clear()
		return update
		
	def get_full(self, player=None):
		if player is None:
			return {p:v.get_log() for p,v in self.writers.items()}
		return self.writers[player].get_log()



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