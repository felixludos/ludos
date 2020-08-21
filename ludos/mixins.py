
import time
import numpy as np

from humpack import Packable, Transactionable, Hashable
from humpack.packing import primitive

class Named(object):
	'''
	Creates a name that must be provided in __init__
	'''
	def __init__(self, name, *args, **kwargs):
		'''
		
		:param name: Must be provided for this mixin, the name should usually be provided as a keyword argument.
		:param args: Any other positional arguments to be passed on with super()
		:param kwargs: Any other keyword arguments to be passed on with super()
		'''
		super().__init__(*args, **kwargs)
		self.name = name
	
	def __str__(self):
		'''
		By default, Named objects use the name as __str__
		:return: name of this object
		'''
		return self.name

class Typed(object):
	'''
	This specifies a type (in the form of a string) saved to "obj_type", which must be passed in in class declaration
	All instances of a type should have the same obj_type
	'''
	
	def __init_subclass__(cls, obj_type=None, **kwargs):
		
		super().__init_subclass__(**kwargs)
		
		if obj_type is None:
			obj_type = cls.__name__
		cls.obj_type = obj_type
	
	def __init__(self, obj_type=None, **kwargs):
		super().__init__(**kwargs)
		if obj_type is not None:
			self.obj_type = obj_type
		
	def get_type(self):
		'''
		Queries the obj_type (not related to type(self))
		:return: obj_type
		'''
		return self.obj_type

class Jsonable(object):
	'''
	Object whose data can be formatted as a json object
	'''
	def jsonify(self):
		'''
		Get data from this object in the form of a json object.
		:return: A json object (only containing dict, list, and primitives)
		'''
		raise NotImplementedError

class Pullable(object):
	'''
	Can provide player specific information in the form of the standard GSM interface
	(eg. game objects visible to a certain player).
	'''
	def pull(self, player=None):  # output should be full json readable
		'''
		Get player specific information using GSM interface.
		:param player: Optional to filter out information only visible to this player,
		otherwise returns only information visible to all players.
		:type player: gsm.core.GamePlayer
		:return: Must return a json object (only dict, list, and primitives)
		'''
		raise NotImplementedError
	
	
class Writable(object):
	'''
	Can reformat object data to be written to a log.
	To be writable this object must provide a "text value" which is a string of data that can be directly printed,
	a "text type" which should be a string meant to specify certain formatting, and "text info" which is a dict
	(string -> primitive) of any information.
	'''
	
	def get_text_val(self):
		'''
		The "text value" is the string of data that should be directly printable
		
		:return: text that can be displayed without formatting
		:rtype: str
		'''
		raise NotImplementedError
	
	def get_text_type(self):
		'''
		The "text type" is a string which should specify a specific kind of formatting for this type of object.
		:return: type of object that is written
		:rtype: str
		'''
		raise NotImplementedError
	
	def get_text_info(self):
		'''
		Optionally, additional formatting instructions can be provided in the form of a dict here.
		Note that: all keys must be strings and all values must be primitives.
		:return: A dict of additional and optional formatting instructions of the text
		:rtype: dict(str -> {str, int, float, bool})
		'''
		return {}


