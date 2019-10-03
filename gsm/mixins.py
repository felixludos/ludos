
import time
import numpy as np

from humpack import Savable, Transactionable, Hashable
from humpack.saving import _primitives

class Named(object):
	def __init__(self, name, **kwargs):
		super().__init__(**kwargs)
		self.name = name
	
	def __str__(self):
		return self.name

class Typed(object):
	def __init__(self, obj_type, **kwargs):
		super().__init__(**kwargs)
		self.obj_type = obj_type
	
	def get_type(self):
		return self.obj_type

class Jsonable(object):
	def jsonify(self):
		raise NotImplementedError

class Pullable(object):
	def pull(self, player=None):  # output should be full json readable
		raise NotImplementedError
	
	
class Writable(object):
	
	def get_text_val(self):
		raise NotImplementedError
	
	def get_text_type(self):
		raise NotImplementedError
	
	def get_text_info(self):
		return {}



# class Container(Transactionable, Savable): # containers are Savable over Transactionable - ie. transactions are part of the state, so setting the state can change the transaction
# 	pass


# class Trackable(object):
#
# 	def __init__(self, tracker=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self.__dict__['_tracker'] = tracker  # usually should be set manually --> by GameObject
#
# 	def signal(self, *args, **kwargs):  # for tracking
# 		if self._tracker is not None:
# 			return self._tracker.signal(*args, **kwargs)




