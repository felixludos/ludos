
import numpy as np
from scipy.special import softmax

from ...mixins import Named, Typed
from ... import tlist, tdict, tset, theap, Transactionable, Savable
from .. import RandomAgent
from .mind import Idea, StopThinking

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
	def __init__(self, name, stochastic=True, seed=None):
		super().__init__(name, seed=seed)
		self.stochastic = stochastic

		self._mindsets = tdict()
		self._tactics = tdict()
		
		self.mind = tdict()
		
	def register_mindset(self, phase, mindset):
		if phase not in self._mindsets:
			self._mindsets[phase] = tlist()
		self._mindsets[phase].append(mindset)
		
	def register_tactic(self, phase, group, tactic):
		if phase not in self._tactics:
			self._tactics[phase] = tdict()
		if group not in self._tactics[phase]:
			self._tactics[phase][group] = tlist()
		self._tactics[phase][group].append(tactic)
	
	def _observe(self, me, phase, **status):
		
		self.phase = phase
		self.think(me, phase=phase, **status)
		
		if phase in self._mindsets:
			for mindset in self._mindsets[phase]:
				mindset.observe(self.mind, me=me, phase=phase, **status)
		
		if phase in self._tactics:
			for tactic in self._tactics[phase].values():
				tactic.observe(self.mind, me, **status)
		
	
	def think(self, me, **status):
		pass
	
	
	def _decide(self, options):
		
		mindsets = self._mindsets[self.phase]
		tactics = None if self.phase is None else self._tactics[self.phase]
		
		groups = list(options.keys())
		
		values = np.zeros(len(options))
		for mindset in mindsets:
			values += mindset.prioritize(self.mind, groups)
		
		wts = softmax(values)
		
		group = self.gen.choices(groups, weights=wts, k=1)[0] if self.stochastic else groups[wts.argmax()]
		
		if tactics is None or group not in tactics:
			action = self.gen.choice(options[group])
		
		elif len(tactics[group]) > 1:
			tvals = [tactic.priority(self.mind, options[group]) for tactic in tactics]
			twts = softmax(tvals)
			tactic = self.gen.choices(tactics, weights=twts, k=1)[0] if self.stochastic else tactics[twts.argmax()]
			action = tactic.decide(self.mind, options[group])
		
		else:
			tactic = self._tactics[self.phase][group]
			action = tactic.decide(self.mind, options[group])
		
		return group, self.package_action(action)
		



