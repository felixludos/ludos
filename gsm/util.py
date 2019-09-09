from .containers import tdict
from .mixins import Named, Typed
from .containers import tdict, tset, tlist

def jsonify(obj):
	if isinstance(obj, (list, tlist)):
		return [jsonify(o) for o in obj]
	if isinstance(obj, (dict, tdict)):
		return {jsonify(k):jsonify(v) for k,v in obj.items()}
	if isinstance(obj, tuple):
		return {'tuple': [jsonify(o) for o in obj]}
		# return [jsonify(o) for o in obj]
	if isinstance(obj, (set, tset)):
		return {'set': [jsonify(o) for o in obj]}
	return obj

def unjsonify(obj):
	if isinstance(obj, list):
		return tlist([unjsonify(o) for o in obj])
	if isinstance(obj, dict):
		if 'set' in obj and len(obj) == 1:
			return tset([unjsonify(o) for o in obj['set']])
		if 'tuple' in obj and len(obj) == 1:
			return tuple(unjsonify(o) for o in obj['tuple'])
		return tdict({unjsonify(k):unjsonify(v) for k,v in obj.items()})
	return obj


class Player(Named, Typed, tdict):
	def __init__(self, name):
		super().__init__(name, self.__class__.__name__)

	def __hash__(self):
		return hash(self.name)
	def __eq__(self, other):
		return other == self.name