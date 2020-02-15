
import numpy as np
from scipy.special import softmax

from ...mixins import Named, Typed
from ... import tlist, tdict, tset, theap, Transactionable, Packable
from .. import RandomAgent
from .mind import Idea, StopThinking, DontAskMe

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
		
	def register_mindset(self, mindset):
		phase = mindset.get_type()
		if phase not in self._mindsets:
			self._mindsets[phase] = tlist()
		self._mindsets[phase].append(mindset)
		
	def register_tactic(self, tactic):
		phase, group = tactic.get_type(), tactic.name
		if phase not in self._tactics:
			self._tactics[phase] = tdict()
		if group not in self._tactics[phase]:
			self._tactics[phase][group] = tlist()
		self._tactics[phase][group].append(tactic)
	
	def _observe(self, me, phase, options, **status):
		
		self.phase = phase
		self.think(me, phase=phase, options=options, **status)
		
		if phase in self._mindsets:
			for mindset in self._mindsets[phase]:
				mindset.observe(self.mind, me=me, phase=phase, options=options, **status)
		
		if phase in self._tactics:
			for group, tactics in self._tactics[phase].items():
				if group in options:
					for tactic in tactics:
						tactic.observe(self.mind, me, options=options, **status)
		
	
	def think(self, me, **status):
		pass
	
	
	def _decide(self, options):
		
		mindsets = self._mindsets[self.phase] if self.phase in self._mindsets else []
		tactics = self._tactics[self.phase] if self.phase in self._tactics else None
		
		groups = list(options.keys())
		
		values = np.zeros(len(options))
		for mindset in mindsets:
			values += mindset.prioritize(self.mind, groups)
		
		wts = softmax(values)
		
		group = self.gen.choices(groups, weights=wts, k=1)[0] if self.stochastic else groups[wts.argmax()]
		
		action = None
		if tactics is not None and group in tactics:
			if len(tactics[group]) > 1:
				tvals = [tactic.priority(self.mind, options[group]) for tactic in tactics]
				twts = softmax(tvals)
				tactic = self.gen.choices(tactics, weights=twts, k=1)[0] if self.stochastic else tactics[twts.argmax()]
			else:
				tactic = tactics[group][0]
			try:
				action = tactic.decide(self.mind, options[group])
			except DontAskMe:
				pass
		
		if action is None:
			action = self.package_action(self.gen.choice(list(options[group])))
			print('Choosing random action: {}'.format(action))
		
		return group, action
		



