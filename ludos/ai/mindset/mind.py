
import numpy as np

from ...mixins import Named, Typed
from ... import glist, gdict, gset, gheap, Transactionable, Packable
from .. import RandomAgent

class Tactic(Typed, Named, gdict):
	
	def observe(self, mind, me, **status):
		pass
	
	def priority(self, mind, actions):
		return 0.
	
	def decide(self, mind, actions):
		raise NotImplementedError

class StopThinking(Exception):
	pass
class DontAskMe(Exception):
	pass


class Mindset(Typed, gdict): # high level goal
	
	def observe(self, mind, me, **status):
		pass
	
	def prioritize(self, mind, groups):
		raise NotImplementedError # returns array of floats of corresponding priorities of each group


class Random_Tactic(Tactic):
	def __init__(self, phase, group, gen):
		super().__init__(phase, group)
		self.gen = gen
	
	def decide(self, mind, actions):
		return self.gen.choice(actions)


class Random_Mindset(Mindset):
	def __init__(self, phase, gen):
		super().__init__(phase)
		self.gen = gen
	
	def prioritize(self, mind, groups):
		return np.array([self.gen.gauss(0, 1) for _ in range(len(groups))])



class Idea(gdict):
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
