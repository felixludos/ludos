
from humpack import tset, tdict, tlist
from .object import GameObject
from .player import GamePlayer
from ..writing import RichWriter, LogWriter, write, writef
from ..mixins import Named, Typed, Packable, Transactionable, Pullable
# from ..util import Player
from string import Formatter

'''
log formatting:
- players
- game objects
- structure - print to different levels (increment or reset)
'''

class GameLogger(Packable, Transactionable, Pullable):
	def __init__(self, indent_level=None, debug=False, end='\n'):
		
		self.log = tlist()
		self.update = None
		
		self.debug = debug
		self.indent_level = indent_level
		self.end = end
		self._shadow = None
		
		self.players = None
		self.targets = None
	
	def reset(self, players):
		self.players = tlist(players)
		self.clear()
		self.update = tdict({player:tlist() for player in self.players})
	
	def __pack__(self):
		pack = self.__class__._pack_obj
		data = {
			'debug': pack(self.debug),
			'indent_level': pack(self.indent_level),
			'end': pack(self.end),
			'players': pack(self.players),
			'targets': pack(self.targets),
			'log': pack(self.log),
			'update': pack(self.update),
			'_shadow': pack(self._shadow),
		}
		return data
	
	def __unpack__(self, data):
		unpack = self.__class__._unpack_obj
		
		self.debug = unpack(data['debug'])
		self.indent_level = unpack(data['indent_level'])
		self.end = unpack(data['end'])
		
		self.players = unpack(data['players'])
		self.targets = unpack(data['targets'])
		
		self.update = unpack(data['update'])
		self.log = unpack(data['log'])
		self._shadow = unpack(data['_shadow'])
		
	def begin(self):
		if self.in_transaction():
			return
		self.log.begin()
		self.update.begin()
		self._shadow = tdict()
		self._shadow.debug = self.debug
		self._shadow.indent_level = self.indent_level
		self._shadow.end = self.end
		self._shadow.players = self.players
		self._shadow.targets = self.targets
		
	def in_transaction(self):
		return self._shadow is not None
		
	def commit(self):
		if not self.in_transaction():
			return
		self._shadow = None
		self.log.commit()
		self.update.commit()
	
	def abort(self):
		if not self.in_transaction():
			return
		self.debug = self._shadow.debug
		self.indent_level = self._shadow.indent_level
		self.end = self._shadow.end
		self.players = self._shadow.players
		self.targets = self._shadow.targets
		self._shadow = None
		self.log.abort()
		self.update.abort()
	
	def __getitem__(self, item):
		if isinstance(item, (tuple, list, set)):
			self.targets = list(item)
		else:
			self.targets = [item]
		return self
	
	def zindent(self):  # reset indent
		if self.indent_level is not None:
			self.indent_level = 0
	
	def iindent(self, n=1):  # increment indent
		if self.indent_level is not None:
			self.indent_level += n
	
	def dindent(self, n=1):  # decrement indent
		if self.indent_level is not None:
			self.indent_level = max(self.indent_level - n, 0)
		
	def clear(self):
		self.log.clear()
		
	def __len__(self):
		return len(self.log)
		
	def _add_line(self, line):
		targets = self.targets
		if self.targets is not None and len(self.targets):
			line['targets'] = self.targets
		self.log.append(line)
		for update in self.update.values():
			update.append(line)
		self.targets = None
		
	def write(self, *objs, end=None, indent_level=None):
		if end is None:
			end = self.end
		if indent_level is None:
			indent_level = self.indent_level
		
		line = write(*objs, end=end, indent_level=indent_level)
		return self._add_line(line)
	
	def writef(self, txt, *objs, end=None, indent_level=None, **kwobjs):
		
		if end is None:
			end = self.end
		if indent_level is None:
			indent_level = self.indent_level
		
		line = writef(txt, *objs, end=end, indent_level=indent_level, **kwobjs)
		return self._add_line(line)
		
	def filter_log(self, log, player=None, god_mode=False):
		update = []
		for line in log:
			if god_mode \
					or 'targets' not in line \
					or (player is not None and player in line['targets']):
				update.append(line)
		
		return update
		
	def get_full(self, player=None, god_mode=False):
		return self.filter_log(self.log, player=player, god_mode=god_mode)
		
	def pull(self, player=None, god_mode=False):
		if player is None:
			return self.filter_log(self.log, player=player, god_mode=god_mode)
		
		update = self.filter_log(self.update[player], player=player, god_mode=god_mode)
		self.update[player].clear()
		return update


class OldGameLogger(LogWriter):
		
	def reset(self, players):
		self.writers = tdict({p: LogWriter(indent_level=self.indent_level, debug=self.debug)
		                      for p in players})
		
		super().reset()
		
	def __pack__(self):
		data = super().__pack__()
		data['writers'] =  self.__class__._pack_obj(self.writers)
		return data
	
	def __unpack__(self, data):
		super().__unpack__(data)
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
		if player is None: # god mode - get all logs
			return {p:v.get_log() for p,v in self.writers.items()}
		if player not in self.writers:
			return self.get_log()
		return self.writers[player].get_log()



# TODO: add formats for headings, lists, maybe images, ...
# TODO: make sure frontend can handle some basic/standard format instructions

