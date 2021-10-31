import sys, os
from pathlib import Path
import random

from omnibelt import load_yaml, load_txt

import gsm
from gsm import Game

class WiseOtherwise(Game, name='wise'):
	def __init__(self, seed=None, allow_duplicates=False, **kwargs):
		if seed is None:
			seed = random.getrandbits(32)
		random.seed(seed)
		super().__init__(seed=seed)
		self._seed = seed

		self._query = None
		self._queries = None
		self._responses = None
	
	def _pick_query(self):
		pick = random.randint(0,len(self._queries)-1)
		self._query = self._queries[pick]
		del self._queries[pick]
	
	def _load_data(self, root):
		root = Path(root)
		
		spath = root / 'starts.yaml'
		data = load_yaml(spath)
		raw = load_txt(spath).split('\n')
		nums = [int(r[2:]) for r in raw if len(r) and r[0] == '#']
		starts = {n: data[i * 5:(i + 1) * 5] for i, n in enumerate(nums)}
		
		epath = root / 'ends.yaml'
		ends = load_yaml(epath)
		
		for i, lines in starts.items():
			for line, end in zip(lines, ends[i]):
				line['end'] = end
		return [line for ind in sorted(list(starts.keys())) for line in starts[ind]]
	
	def _standard_actions(self):
		actions = {}
		for player in self.players:
			if player not in self._responses:
				crt = gsm.GameController()
				crt.add_group('respond', 'Write a response', [gsm.TextAction()])
				# crt.add_group('skip', 'Vote to skip this saying')
				actions[player] = crt
		return actions
		
	def _start_round(self):
		self._pick_query()
		
		self.state.query = self._query
		
		self._responses = {}
		# self._skips = {}
	
	
	
	def begin_game(self):
		self._queries = self._load_data(self.root / 'test-data') # TESTING
		self._start_round()
		return self._standard_actions()
	
	
	
	
	
		


