
from humpack import tset, tdict, tlist
from ..errors import OverwritingDataError

class GameState(tdict):
	pass

class GameData(tdict):
	def __new__(cls, *args, **kwargs):
		obj = super().__new__(cls, *args, **kwargs)
		obj.__dict__['_lock'] = False
		return obj
	
	def lock(self):
		self.__dict__['_lock'] = True
	
	def __setattr__(self, key, value):
		if self.__dict__['_lock']:
			raise OverwritingDataError
		return super().__setattr__(key, value)

