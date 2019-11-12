
from ...mixins import Named, Typed
from ... import tlist, tdict, tset, theap, Transactionable, Savable
from .. import RandomAgent

class Tactic(Typed, Named, tdict):
	
	def observe(self, me, **status):
		pass
	
	def decide(self, mind, actions):
		raise NotImplementedError

class StopThinking(Exception):
	pass

class Mindset(tdict): # high level goal
	
	def process(self, me, **status):
		return 0 # returns int of how important it is to edit current mindset
	
	def edit(self, mind):
		return mind

class Idea(tdict):
	def __init__(self, rank, *args, **items):
		super().__init__(*args, **items)
		self.rank = rank
	
	def __cmp__(self, other):
		return other.rank - self.rank
	
	def __gt__(self, other):
		return self.__cmp__(other) > 0
	def __ge__(self, other):
		return self.__cmp__(other) >= 0
	def __lt__(self, other):
		return self.__cmp__(other) < 0
	def __le__(self, other):
		return self.__cmp__(other) <= 0

class Killer_Idea(Idea):
	def __init__(self, *args, rank=None, **items):
		super().__init__(*args, rank=None, **items)
	
	def __cmp__(self, other):
		return -1 # this is always first
