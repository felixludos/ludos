
from string import Formatter

from .basic_containers import tdict, tset, tlist
from .mixins import Typed, Savable, Transactionable, Pullable
from .signals import FormatException
from .util import Player

FMT = Formatter()

class RichWriter(Savable, Transactionable, Pullable):
	
	def __init__(self, indent=None, debug=False):
		super().__init__()
		
		self.text = tlist()
		
		self.debug = debug
		self.indent_level = indent
		self._shadow_indent = None
	
	def zindent(self):  # reset indent
		if self.indent_level is not None:
			self.indent_level = 0
	
	def iindent(self, n=1):  # increment indent
		if self.indent_level is not None:
			self.indent_level += n
	
	def dindent(self, n=1):  # decrement indent
		if self.indent_level is not None:
			self.indent_level = max(self.level - n, 0)
	
	def _process_obj(self, obj):
		info = {}
		if isinstance(obj, RichText):
			info.update(obj.get_info())
			info['type'] = obj.get_type()
			info['val'] = obj.get_val()
		elif isinstance(obj, Player):
			info['type'] = 'player'
			info['val'] = obj.name
		elif isinstance(obj, Typed):
			info['type'] = obj.get_type()
			info['val'] = str(obj)
		else:
			info['type'] = obj.__class__.__name__
			info['val'] = str(obj)
		
		return info
	
	def write(self, *objs, end='\n', indent_level=None, player=None, debug=False):
		
		if debug and not self.debug:  # Dont write a debug line unless specified
			return
		
		if indent_level is None:
			indent_level = self.level
		
		if len(end):
			objs.append(end)
		
		line = {
			'line': [self._process_obj(obj) for obj in objs],
		}
		
		if indent_level is not None:
			line['level'] = indent_level
		
		self._log(line, player=player)
	
	def writef(self, txt, *objs, end='\n', indent_level=None, player=None, debug=False, **kwobjs):
		
		line = []
		
		pos = 0
		
		for pre, info, spec, _ in FMT.parse(txt):
			
			line.append(pre)
			
			if info is None:
				continue
			elif info in kwobjs:
				obj = kwobjs[info]
			else:
				try:
					obj = objs[int(info)]
				except ValueError:
					if info == '':
						obj = objs[pos]
						pos += 1
					else:
						raise FormatException('Unknown object info, type {}: {}'.format(type(info), info))
			
			if spec is not None:
				obj = obj.__format__(spec)
			
			line.append(obj)
		
		self.write(*line, end=end, indent_level=indent_level, player=player, debug=debug)
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['text'] = pack(self.text)
		data['indent_level'] = pack(self.indent_level)
		data['_shadow_indent'] = pack(self._shadow_indent)
		data['debug'] = pack(self.debug)
		
		return data

	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		
		self = cls()
		
		self.text = unpack(data['text'])
		self.indent_level = unpack(data['indent_level'])
		self._shadow_indent = unpack(data['_shadow_indent'])
		self.debug = unpack(data['debug'])
		
		return self
		

	def begin(self):
		if self.in_transaction():
			self.commit()

		self._shadow_indent = self.indent_level
		self.text.begin()

	def in_transaction(self):
		return self.text.in_transaction()

	def commit(self):
		if not self.in_transaction():
			return

		self.text.commit()
		self._shadow_indent = None

	def abort(self):
		if not self.in_transaction():
			return

		self.text.abort()
		self.indent_level = self._shadow_indent
		self._shadow_indent = None
		
		
	def pull(self):
		return list(self.text)


# the dev can write instance of RichText, but all written objects are stored as simple objects (dict, list, primitives)
class RichText(Typed, Savable):
	
	def __init__(self, msg, obj_type=None, **info):
		if obj_type is None:
			obj_type = self.__class__.__name__
		super().__init__(obj_type)
		self.val = msg
		self.info = info
	
	def get_val(self):
		return self.val
	
	def get_info(self): # dev can provide frontend with format instructions, this is added to the info for each line in the log using this LogFormat
		return {} # by default no additional info is sent
	
	def __save(self):
		pack = self.__class__.__pack
		
		return {
			'val' :pack(self.val),
			'info' :pack(self.info),
		}
	
	@classmethod
	def __load(cls, data):
		return cls(cls.__unpack(data['val']), **cls.__unpack(data['info']))
	
	def __format__(self, format_spec):
		raise NotImplementedError

class WarningText(RichText):
	def __init__(self, msg):
		super().__init__(msg, 'Warning')

# def get_info(self):
# 	return tdict(color='yellow') # example

class ErrorText(RichText):
	def __init__(self, msg):
		super().__init__(msg, 'Error')

