
import json
import random
from itertools import chain
from .basic_containers import tset, tdict, tlist
from .core.object import obj_unjsonify
from .core.actions import decode_action_set
from .util import unjsonify

def _format(obj):
	return unjsonify(json.loads(obj))

class Ipython_Interface(object):
	
	def __init__(self, controller, seed=None):
		super().__init__()
		
		self.ctrl = controller
		
		self.msg = None
		self.table = None
		if seed is None:
			seed = random.getrandbits(64)
		self.rng = random.Random(seed)
		self.seed = seed
		
		
	def set_player(self, player=None):
		
		if player is None:
			player = self.rng.choice(self.get_players())
		
		self.player = player
		print('Player set to {}'.format(self.player))
		
	def get_player(self, player):
		return _format(self.ctrl.get_player(player))
	
	def get_players(self):
		return _format(self.ctrl.get_players())
	
	
	
	def get_table(self, player=None):
		self.table = _format(self.ctrl.get_table(player=player))
	
	def get_obj_types(self):
		return _format(self.ctrl.get_obj_types())
	
	def get_log(self, player):
		return _format(self.ctrl.get_log(player))
	
	def get_IU_spec(self):
		return _format(self.ctrl.get_UI_spec())
	
	def get_status(self, player=None):
		if player is None:
			player = self.player
		
		self.msg = _format(self.ctrl.get_status(player))
		
		
	
	def reset(self, player=None, seed=None):
		if player is None:
			player = self.player
		self.msg = _format(self.ctrl.reset(player=player, seed=seed))
		
		if 'error' in self.msg:
			print('*** ERROR: {} ***'.format(self.msg.error.type))
			print(self.msg.error.msg)
			print('****************************')
		
	def step(self):
		pass


def print_response(msg):
	
	msg = unjsonify(msg)
	
	if 'error' in msg:
		print('*** ERROR: {} ***'.format(msg.error.type))
		print(msg.error.msg)
		print('****************************')
		
		return msg.table, None
		
	else:
		pass


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
		
		
		
