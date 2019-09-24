
from string import Formatter

from .basic_containers import tdict, tset, tlist
from .mixins import Typed, Savable, Transactionable, Pullable, Writable
from .signals import FormatException

FMT = Formatter()

def _process_obj(obj):
	info = {}
	if isinstance(obj, Writable):
		info.update(obj.get_text_info())
		info['type'] = obj.get_text_type()
		info['val'] = obj.get_text_val()
	elif isinstance(obj, Typed):
		info['type'] = obj.get_type()
		info['val'] = str(obj)
	else:
		info['type'] = obj.__class__.__name__
		info['val'] = str(obj)
	
	return info

def write(*objs, end='\n'):
	
	if end is not None and len(end):
		objs.append(end)
	
	return [_process_obj(obj) for obj in objs]

def writef(txt, *objs, end=None, **kwobjs):
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
		
	return write(line, end=end)

class RichWriter(Savable, Transactionable, Pullable):
	
	def __init__(self, indent=None, debug=False, end='\n'):
		super().__init__()
		
		self.text = tlist()
		
		self.debug = debug
		self.indent_level = indent
		self._shadow_indent = None
		self._in_transaction = None
		self.end = end
	
	def zindent(self):  # reset indent
		if self.indent_level is not None:
			self.indent_level = 0
	
	def iindent(self, n=1):  # increment indent
		if self.indent_level is not None:
			self.indent_level += n
	
	def dindent(self, n=1):  # decrement indent
		if self.indent_level is not None:
			self.indent_level = max(self.indent_level - n, 0)
	
	def clear(self):
		self.text.clear()
		
	def __len__(self):
		return len(self.text)
	
	def write(self, *objs, end=None, indent_level=None, debug=False):
		
		if debug and not self.debug:  # Dont write a debug line unless specified
			return
		
		if indent_level is None:
			indent_level = self.indent_level
			
		line = write(*objs, end=end)
		
		if indent_level is not None:
			line = {
				'line': line,
				'level': indent_level,
			}
		
		self.text.extend(line)
		
	def writef(self, txt, *objs, end=None, indent_level=None, debug=False, **kwobjs):
		
		if debug and not self.debug:  # Dont write a debug line unless specified
			return
		
		if indent_level is None:
			indent_level = self.indent_level
		
		line = writef(txt, *objs, end=end, **kwobjs)
		
		if indent_level is not None:
			line = {
				'line': line,
				'level': indent_level
			}
			
		self.text.extend(line)
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['text'] = pack(self.text)
		data['indent_level'] = pack(self.indent_level)
		data['_shadow_indent'] = pack(self._shadow_indent)
		data['debug'] = pack(self.debug)
		data['in_transaction'] = pack(self._in_transaction)
		data['end'] = pack(self.end)
		
		return data

	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		
		self = cls()
		
		self.text = unpack(data['text'])
		self.indent_level = unpack(data['indent_level'])
		self._shadow_indent = unpack(data['_shadow_indent'])
		self.debug = unpack(data['debug'])
		self._in_transaction = unpack(data['in_transaction'])
		self.end = unpack(data['end'])
		
		return self
		
	def begin(self):
		if self.in_transaction():
			self.commit()

		self._shadow_indent = self.indent_level
		self.text.begin()
		self._in_transaction = True

	def in_transaction(self):
		return self._in_transaction

	def commit(self):
		if not self.in_transaction():
			return

		self.text.commit()
		self._shadow_indent = None
		self._in_transaction = False

	def abort(self):
		if not self.in_transaction():
			return

		self.text.abort()
		self.indent_level = self._shadow_indent
		self._shadow_indent = None
		self._in_transaction = False
		
	def pull(self):
		return list(self.text)


class LogWriter(RichWriter):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.log = tlist()
		
	def begin(self):
		if self.in_transaction():
			self.commit()

		super().begin()
		self.log.begin()

	def commit(self):
		if not self.in_transaction():
			return

		super().commit()
		self.log.commit()

	def abort(self):
		if not self.in_transaction():
			return

		super().abort()
		self.log.abort()
		
	def write(self, *args, **kwargs):
		
		super().write(*args, **kwargs)
		
		self.log.append(self.text[-1])
		
	def get_log(self):
		return list(self.log)
		
	def __save(self):
		
		data = super().__save()
		
		data['log'] = self.__class__.__pack(self.log)
		
		return data
	
	@classmethod
	def __load(cls, data):
		
		obj = super().__load(data)
		obj.log = cls.__unpack(data['log'])
		
		return obj

# the dev can write instance of RichText, but all written objects are stored as simple objects (dict, list, primitives)
class RichText(Typed, Writable, Savable):
	
	def __init__(self, msg, obj_type='Regular', **info):
		super().__init__(obj_type)
		self.val = msg
		self.info = info
	
	def get_text_type(self):
		return self.get_type()
	
	def get_text_val(self):
		return self.val
	
	def get_text_info(self): # dev can provide frontend with format instructions, this is added to the info for each line in the log using this LogFormat
		return self.info # by default no additional info is sent
	
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

