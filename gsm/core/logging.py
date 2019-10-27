
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

