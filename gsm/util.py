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