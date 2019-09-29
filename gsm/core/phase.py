from ..mixins import Named, Transactionable, Savable
from humpack import tset, tdict, tlist
from ..signals import PhaseComplete

class GamePhase(Named, tdict):
	
	# __init__ can be overridden
	def __init__(self, name=None, **info):
		
		if name is None:
			name = self.__class__.__name__
		super().__init__(name, **info)
	
	def execute(self, C, player=None, action=None): # must be implemented
		raise NotImplementedError
	
	def encode(self, C): # by default no actions are necessary
		raise PhaseComplete # this should usually return a GameActions instance
