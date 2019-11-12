
from ...mixins import Named, Typed
from ... import tlist, tdict, tset, theap, Transactionable, Savable
from .. import RandomAgent
from .mind import Idea

class Mind(tdict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._ideas = theap()
	
	def __setitem__(self, key, value):
		if isinstance(value, Idea):
			self._ideas.add(value)
		return super().__setitem__(key, value)
	def __delitem__(self, item):
		if isinstance(item, Idea):
			self._ideas.discard(item)
	
	def ideas(self):
		return self._ideas
	

class Mindset_Agent(RandomAgent):
	def __init__(self, name, seed=None):
		super().__init__(name, seed=seed)

		self._mindsets = tdict()
		self._tactics = tdict()
		
		self.mind = tdict()
		
	def register_mindset(self, phase, group, mindset):
		pass
	
	def register_tactic(self, phase, group, tactic):
		pass
	
	def observe(self, me, **status):
		pass
	
	def decide(self, options):
		pass



