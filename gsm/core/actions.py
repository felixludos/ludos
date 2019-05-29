import json
from ..structures import tdict, tset, tlist

def jsonify_actions(obj):
	if isinstance(obj, tuple):
		return [jsonify_actions(o) for o in obj]
	elif isinstance(obj, set):
		return {'set': [jsonify_actions(o) for o in obj]}
	else:
		return obj

class GameActions(object):
	
	def __init__(self):
		self.pairs = []
	
	def add(self, options, instructions=None):
		
		segment = {'options': jsonify_actions(options)}
		
		if instructions is not None:
			assert isinstance(instructions, str), 'invalid instruction type'
			segment['instructions'] = instructions
		
		self.pairs.append(segment)
	
	def pull(self):
		return json.dumps(self.pairs)

