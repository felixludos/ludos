from .containers import tdict
from .mixins import Named, Typed


class Player(Named, Typed, tdict):
	def __init__(self, name):
		super().__init__(name, self.__class__.__name__)

	def __hash__(self):
		return hash(self.name)
	def __eq__(self, other):
		return other == self.name