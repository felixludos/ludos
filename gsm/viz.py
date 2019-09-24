
import json
import random
from itertools import chain
from .basic_containers import tset, tdict, tlist
from .core.object import obj_unjsonify
from .core.actions import decode_action_set
from .util import unjsonify

def _format(obj):
	return unjsonify(json.loads(obj))

def _format_line(line):
	
	txt = []
	
	for obj in line:
		if isinstance(obj, dict):
			if obj['type'] == 'player':
				txt.append('P:{}'.format(obj['val']))
			elif obj['type'] == 'obj':
				txt.append('O:{}'.format(obj['val']))
			else:
				raise Exception('cant handle: {}'.format(repr(obj)))
		else: # obj is a str
			txt.append(str(obj))
		
	return ''.join(txt)

def _format_action(tpl):
	
	action = []
	
	for obj in tpl:
		if obj['type'] == 'fixed':
			action.append(obj['val'])
		else:
			raise Exception('cant handle: {}'.format(repr(obj)))
		
	return tuple(action)
	
def _package_action(action):
	
	final = []
	
	for obj in action:
		
		if obj['type'] == 'fixed':
			final.append(obj['val'])
		else:
			raise Exception('cant handle: {}'.format(repr(obj)))

	return tuple(final)


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
		
		self.actions = None
		self.action = None
		
		self.waiting_for = None
		
		self.player = None
		self.key = None
		
	def save(self):
		return self.ctrl.save()
	
	def load(self, data):
		return self.ctrl.load(data)
	
	def set_player(self, player=None):
		
		if player is None:
			if self.msg is None or 'waiting_for' not in self.msg:
				player = self.rng.choice(self.get_players())
			player = self.msg.waiting_for.pop()
		
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
		
		self._process_msg()
		
	def _process_msg(self):
		
		if 'error' in self.msg:
			print('*** ERROR: {} ***'.format(self.msg.error.type))
			print(self.msg.error.msg)
			print('****************************')
		
		if 'options' in self.msg:
			self.actions = tlist()
			
			for opt in self.msg.options:
				self.actions.extend(decode_action_set(opt.actions))
				
		if 'key' in self.msg:
			self.key = self.msg.key
		
		if 'table' in self.msg:
			self.table = self.msg.table
			
		# if 'waiting_for' in self.msg:
		# 	print('Waiting for: {}'.format(', '.join(self.msg.waiting_for)))
	
	def reset(self, player=None, seed=None):
		if player is None:
			player = self.player
		self.msg = _format(self.ctrl.reset(player=player, seed=seed))
		
		self._process_msg()
				
		
	def view(self):
		if self.msg is None:
			print('No message found')
			return
		
		if 'info' in self.msg:
			print('Received info: {}'.format(list(self.msg.info.keys())))
		
		if 'key' in self.msg:
			print('Received key: {}'.format(self.msg.key))
		
		if 'table' in self.msg:
			print('Received table: {} entries'.format(len(self.msg.table)))
		
		if 'log' in self.msg:
			print('-------------')
			print('Log')
			print('-------------')
			
			print(_format_line(self.msg.log))
			
		
		if 'error' in self.msg:
			print('*** ERROR: {} ***'.format(self.msg.error.type))
			print(self.msg.error.msg)
			print('****************************')
		
		if 'waiting_for' in self.msg:
			print('Waiting for: {}'.format(', '.join(self.msg.waiting_for)))
		else:
			
			if 'status' in self.msg:
				status = _format_line(self.msg.status)
				print('+' + '-' * (len(status) + 2) + '+')
				print('| {} |'.format(status))
				print('+' + '-' * (len(status) + 2) + '+')
				
				# print('Status: {}'.format(_format_line(self.msg.status)))
			else:
				print('No status found')
		
			if 'options' in self.msg:
				idx = 0
				
				for opt in self.msg.options:
					
					if 'desc' in opt:
						print('-- {} --'.format(_format_line(opt.desc)))
					
					for tpl in decode_action_set(opt.actions):
						print('{:>4} - {}'.format(idx, _format_action(tpl)))
						idx += 1
					
		
			
	def view_info(self):
		if self.msg is None or 'info' not in self.msg:
			print('No info to print')
		return render_dict(self.msg.info)
		
	def view_table(self):
		if self.table is None:
			print('No table to print')
			
		return render_dict(self.table)
		
	def select_action(self, idx=None):
		
		if idx is None:
			idx = self.rng.randint(0,len(self.actions)-1)
		
		self.action = self.actions[idx]
		
		print('Selected action {}: {}'.format(idx, _format_action(self.action)))
	
	
	def step(self):
		
		if self.action is None:
			print('Must first select an action')
			
		if self.key is None:
			print('No key found')
		
		self.msg = _format(self.ctrl.step(player=self.player, action=_package_action(self.action), key=self.key))
		
		self.key = None
		
		self._process_msg()
		
		self.action = None
		self.actions = None









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
		
		
		
