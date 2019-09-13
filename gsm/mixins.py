
import numpy as np
# from .signals import UnregisteredClassError

class Savable(object):
	_subclasses = {}
	
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._subclasses[cls.__name__] = cls

	@classmethod
	def get_cls(cls, name):
		try:
			return cls._subclasses[name]
		except KeyError:
			raise UnregisteredClassError(name)

	def __getstate__(self):
		raise NotImplementedError
	
	def __setstate__(self, state):
		raise NotImplementedError


class Named(object):
	def __init__(self, name=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
	
	def __str__(self):
		return self.name

class Typed(object):
	def __init__(self, obj_type=None, **kwargs):
		super().__init__(**kwargs)
		self.obj_type = obj_type
	
	def get_type(self):
		return self.obj_type


class Transactionable(object):
	
	def begin(self):
		raise NotImplementedError
	
	def in_transaction(self):
		raise NotImplementedError
	
	def commit(self):
		raise NotImplementedError
	
	def abort(self):
		raise NotImplementedError

	# def __enter__(self):
	# 	# self._context = True
	# 	self.begin()
	#
	# def __exit__(self, type, *args):
	# 	# self._context = False
	# 	if type is None:
	# 		self.commit()
	# 	else:
	# 		self.abort()
	# 	return None if type is None else type.__name__ == 'AbortTransaction'


# class Trackable(object):
#
# 	def __init__(self, tracker=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self.__dict__['_tracker'] = tracker  # usually should be set manually --> by GameObject
#
# 	def signal(self, *args, **kwargs):  # for tracking
# 		if self._tracker is not None:
# 			return self._tracker.signal(*args, **kwargs)