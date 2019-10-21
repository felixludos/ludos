
import numpy as np

from gsm import GameObject
from gsm.common.world import Grid, Field


class Board(Grid):
	
	def check(self):
		L = self.map.shape[0]
		
		# check rows
		sums = self.map.sum(0)
		
		if (sums == L).any():
			return 1
		elif (sums == -L).any():
			return -1
		
		# check cols
		sums = self.map.sum(1)
		
		if (sums == L).any():
			return 1
		elif (sums == -L).any():
			return 1
		
		# check diag
		diag = np.diag(self.map).sum()
		if diag == L:
			return 1
		elif diag == -L:
			return -1
		
		diag = np.diag(np.fliplr(self.map)).sum()
		if diag == L:
			return 1
		elif diag == -L:
			return -1
		
		return 0
		
	def get_free(self):
		free = self.map == 0
		return self.map[free]


class Tick(Field):
	def __init__(self, **props):
		super().__init__(**props)
		
		self._val = 0
		
	def __eq__(self, other):
		try:
			return self._val == other._val
		except AttributeError:
			return self._val == other

	def __hash__(self):
		return super().__hash__()

	def __add__(self, other):
		try:
			return self._val + other._val
		except AttributeError:
			return self._val + other
		
	def __radd__(self, other):
		return self.__add__(other)
		
	def __str__(self):
		return '({},{})'.format(self.row, self.col)