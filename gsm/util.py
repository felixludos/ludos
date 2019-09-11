import yaml
import numpy as np
from .containers import tdict
from .mixins import Named, Typed
from .containers import tdict, tset, tlist

def jsonify(obj):
	if isinstance(obj, (list, tlist)):
		return [jsonify(o) for o in obj]
	if isinstance(obj, (dict, tdict)):
		return {jsonify(k):jsonify(v) for k,v in obj.items()}
	if isinstance(obj, tuple):
		return {'_tuple': [jsonify(o) for o in obj]}
		# return [jsonify(o) for o in obj]
	if isinstance(obj, (set, tset)):
		return {'_set': [jsonify(o) for o in obj]}
	if isinstance(obj, np.ndarray): # TODO: make this work for obj.dtype = 'obj', maybe recurse elements of .tolist()?
		return {'_ndarray': obj.tolist(), '_dtype':obj.dtype}
	return obj

def unjsonify(obj):
	if isinstance(obj, list):
		return tlist([unjsonify(o) for o in obj])
	if isinstance(obj, dict):
		if '_set' in obj and len(obj) == 1:
			return tset([unjsonify(o) for o in obj['set']])
		if '_tuple' in obj and len(obj) == 1:
			return tuple(unjsonify(o) for o in obj['tuple'])
		if '_ndarray' in obj and '_dtype' in obj:
			return np.array(obj['_ndarray'], dtype=obj['_dtype'])
		return tdict({unjsonify(k):unjsonify(v) for k,v in obj.items()})
	return obj

def load_config(path):
	return unjsonify(yaml.load(open(path, 'r')))

class Player(Named, Typed, tdict):
	def __init__(self, name, **props):
		super().__init__(name, self.__class__.__name__, **props)

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
