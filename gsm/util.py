import yaml
import numpy as np
import random
from .mixins import Named, Typed, Savable, Transactionable
from .signals import UnregisteredClassError, LoadInitFailureError
from .basic_containers import tdict, tset, tlist

# def load_config(path):
# 	return unjsonify(yaml.load(open(path, 'r')))


class RandomGenerator(random.Random, Savable, Transactionable):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._shadow = None
	
	def copy(self):
		copy = random.Random()
		copy.setstate(self.getstate())
		return copy
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['state'] = pack(list(self.getstate()))
		if self._shadow is not None:
			data['_shadow'] = pack(list(self._shadow))
		
		return data
	
	@classmethod
	def __load(cls, data):
		
		unpack = cls.__unpack
		
		self = cls()
		
		self.setstate(tuple(unpack(data['state'])))
		
		if '_shadow' in data:
			self._shadow = tuple(unpack(data['_shadow']))
		
		return self
		
	
	def begin(self):
		if self.in_transaction():
			self.commit()
		
		self._shadow = self.getstate()
	
	def in_transaction(self):
		return self._shadow is not None
	
	def commit(self):
		if not self.in_transaction():
			return
			
		self._shadow = None
	
	def abort(self):
		if not self.in_transaction():
			return
			
		self.setstate(self._shadow)
		self._shadow = None
		
class Player(Named, Typed, tdict):
	def __init__(self, name=None, **props):
		super().__init__(name=name, obj_type=self.__class__.__name__, **props)

	def __hash__(self):
		return hash(self.name)
	def __eq__(self, other):
		return other == self.name


def render_format(raw):
	if isinstance(raw, set):
		# return list(render_format(el) for el in raw)
		itr = dict()
		for i, el in enumerate(raw):
			itr['s{}'.format(i)] = render_format(el)
		return itr
	elif isinstance(raw, dict):
		return dict((str(k), render_format(v)) for k, v in raw.items())
	elif isinstance(raw, list):
		# return list(render_format(el) for el in raw)
		itr = dict()
		for i, el in enumerate(raw):
			itr['l{}'.format(i)] = render_format(el)
		return itr
	elif isinstance(raw, tuple):
		# return list(render_format(el) for el in raw)
		itr = dict()
		for i, el in enumerate(raw):
			itr['t{}'.format(i)] = render_format(el)
		return itr
	return str(raw)


import uuid
from IPython.display import display_javascript, display_html

class render_dict(object):
	def __init__(self, json_data):
		self.json_str = render_format(json_data)
		
		# if isinstance(json_data, dict):
		#     self.json_str = json_data
		#     #self.json_str = json.dumps(json_data)
		# else:
		#     self.json_str = json
		self.uuid = str(uuid.uuid4())
	
	def _ipython_display_(self):
		display_html('<div id="{}" style="height: 600px; width:100%;"></div>'.format(self.uuid),
		             raw=True
		             )
		display_javascript("""
		require(["https://rawgit.com/caldwell/renderjson/master/renderjson.js"], function() {
		  renderjson.set_show_to_level(1)
		  document.getElementById('%s').appendChild(renderjson(%s))
		});
		""" % (self.uuid, self.json_str), raw=True)


# class Empty(Savable, Transactionable):
#
# 	def __save(self):
# 		raise NotImplementedError
#
# 	@classmethod
# 	def __load(cls, data):
# 		raise NotImplementedError
#
# 	def begin(self):
# 		if self.in_transaction():
# 			self.commit()
#
# 		raise NotImplementedError
#
# 	def in_transaction(self):
# 		raise NotImplementedError
#
# 	def commit(self):
# 		if not self.in_transaction():
# 			return
#
# 		raise NotImplementedError
#
# 	def abort(self):
# 		if not self.in_transaction():
# 			return
#
# 		raise NotImplementedError

