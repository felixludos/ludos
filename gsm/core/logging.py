
from ..basic_containers import tdict, tlist, tset
from .object import GameObject
from ..mixins import Named, Typed, Container
from ..util import Player

'''
log formatting:
- players
- game objects
- structure - print to different levels (increment or reset)
'''


class GameLogger(Container):
	def __init__(self, players=[], indents=True, debug=False):
		super().__init__()
		self.logs = tdict({p: tlist() for p in players})
		self.recent = tdict({p: tlist() for p in players})
		self.collectors = None
		self.debug = debug
		
		self.level = 0 if indents else None
	
	def __save(self):
		pack = self.__class__.__pack
		raise NotImplementedError
	
	def __load(self, data):
		unpack = self.__class__.__unpack
		raise NotImplementedError
	
	def begin(self):
		if self.in_transaction():
			self.commit()
		
		raise NotImplementedError
	
	def in_transaction(self):
		return self._in_transaction
	
	def commit(self):
		if not self.in_transaction():
			return
		
		raise NotImplementedError
	
	def abort(self):
		if not self.in_transaction():
			return
		
		raise NotImplementedError
	
	def update_all(self, objs, player=None):
		if player is not None:
			self.updates[player].extend(objs)
			self.logs[player].extend(objs)
			return
		for update, log in zip(self.updates.values(), self.logs.values()):
			update.extend(objs)
			log.extend(objs)
	
	def zindent(self): # reset indent
		if self.level is not None:
			self.level = 0
	def iindent(self, n=1): # increment indent
		if self.level is not None:
			self.level += n
	def dindent(self, n=1): # decrement indent
		if self.level is not None:
			self.level = max(self.level-n, 0)
	
	def _process_obj(self, obj):
		info = tdict()
		if isinstance(obj, LogFormat):
			info.update(obj.get_info())
			info.type = obj.get_type()
			info.val = obj.get_val()
			
		elif isinstance(obj, Player):
			info.type = 'player'
			info.val = obj.name
			
		elif isinstance(obj, GameObject):
			info.type = 'obj'
			info.obj_type = obj.get_type()
			info.val = obj._id
			
		elif isinstance(obj, Typed):
			info.type = obj.get_type()
			info.val = str(obj)
			
		else:
			info.type = obj.__class__.__name__
			info.val = str(obj)
			
		return info
	
	def write(self, *objs, end='\n', indent_level=None, player=None, debug=False):
	
		if debug and not self.debug: # Dont write a debug line unless specified
			return
	
		if indent_level is None:
			indent_level = self.level
	
		if len(end):
			objs.append(end)
	
		line = tdict(line=tlist(self._process_obj(obj) for obj in objs))
		
		if indent_level is not None:
			line.level = indent_level
		
		self._log(line, player=player)
	
	def writef(self, txt, *objs, end='\n', player=None, **kwobjs):
		raise NotImplementedError # TODO
	
	def _log(self, obj, player=None):
		
		if player is not None:
			self.logs[player].append(obj)
			self.recent[player].append(obj)
		else:
			for log, recent in zip(self.logs.values(), self.recent.values()):
				log.append(obj)
				recent.append(obj)
	
	def pull(self, player):
		log = self.updates[player].copy()
		self.updates[player].clear()
		return log
	
	def get_full(self, player=None):
		if player is not None:
			return self.logs[player].copy()
		return tdict({p: self.logs[p].copy() for p in self.logs})


class LogFormat(Typed):
	
	def __init__(self, obj_type=None):
		if obj_type is None:
			obj_type = self.__class__.__name__
		super().__init__(obj_type)
	
	def get_val(self):
		raise NotImplementedError
	
	def get_info(self): # dev can provide frontend with format instructions, this is added to the info for each line in the log using this LogFormat
		return tdict() # by default no additional info is sent

class LogWarning(LogFormat):
	
	def __init__(self, msg):
		super().__init__('Warning')
		self.val = msg
		
	# def get_info(self):
	# 	return tdict(color='yellow') # example

class LogError(LogFormat):
	
	def __init__(self, msg):
		super().__init__('Error')
		self.val = msg

	# def get_info(self):
	# 	return tdict(color='red') # example

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