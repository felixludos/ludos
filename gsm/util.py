from .structures import xset
from itertools import product, chain
import uuid
from IPython.display import display_javascript, display_html

def jsonify(obj):
	
	if isinstance(obj, dict):
		pass
	elif isinstance(obj, tuple):
		pass
	



def expand_actions(code):
	if isinstance(code, set) and len(code) == 1:
		return expand_actions(next(iter(code)))
	
	if isinstance(code, str) or isinstance(code, int):
		return [code]
	
	# tuple case
	if isinstance(code, (tuple, list)):
		return list(product(*map(expand_actions, code)))
	if isinstance(code, set):
		return chain(*map(expand_actions, code))
	return code

def flatten(bla):
	output = ()
	for item in bla:
		output += flatten(item) if isinstance(item, (tuple, list)) else (item,)
	return output

def decode_actions(code):
	code = expand_actions(code)
	return xset(map(flatten, code))

def seq_iterate(content, itrs, end=False): # None will return that value for each
	if len(itrs) == 0: # base case - iterate over content
		try:
			if end:
				yield content
			else:
				yield from content
		except TypeError:
			yield content
	else: # return only those samples that match specified (non None) tuples
		
		i, *itrs = itrs
		
		if isinstance(content, (list, tuple, set)):
			
			if i is None:
				for x in content:
					yield from seq_iterate(x, itrs, end=end)
			elif isinstance(i, int) and i < len(content):
				yield from seq_iterate(content[i], itrs, end=end)
		
		elif isinstance(content, dict):
			
			if i is None:
				for k, v in content.items():  # expand with id
					for rest in seq_iterate(v, itrs, end=end):
						if isinstance(rest, tuple):
							yield (k,) + rest
						else:
							yield k, rest
			elif i in content:
				yield from seq_iterate(content[i], itrs, end=end)

###############
# Visualize JSON objects in Jupyter
###############

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

