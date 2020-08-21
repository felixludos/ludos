
import json
import random
import pickle
from itertools import chain
from humpack import tset, tdict, tlist, tdeque
from .mixins import Jsonable
from .core.actions import decode_action_set
from .core import GameObject, GamePlayer
from .util import unjsonify, obj_unjsonify, RandomGenerator
from .io import send_http

def _format(obj):
	return unjsonify(json.loads(obj))


def _format_line(line):
	
	txt = []
	
	for obj in line:
		if isinstance(obj, dict):
			if obj['type'] == 'player':
				txt.append('PLYR:{}'.format(obj['val']))
			elif obj['type'] == 'obj':
				txt.append('OBJ[{}]:{}'.format(obj['ID'], obj['val']))
			else:
				raise Exception('cant handle: {}'.format(repr(obj)))
		else: # obj is a str
			txt.append(str(obj))
		
	return ''.join(txt)


def _format_log(lines):
	
	log = []
	
	for line in lines:
		txt = _format_line(line['line'])
		if 'level' in line:
			txt = '-*- ' * line['level'] + txt
		if 'debug' in line:
			txt = '*DEBUG: ' + txt
		
		if 'targets' in line:
			txt = '({}): '.format(', '.join(t for t in line['targets'])) + txt
		log.append(txt)
		
	return ''.join(log)


def _format_action(tpl):
	
	action = []
	
	for obj in tpl:
		if obj['type'] == 'fixed':
			action.append(obj['val'])
		elif obj['type'] == 'obj':
			action.append('OBJ[{}]:{}'.format(obj['ID'], obj['val']))
		elif obj['type'] == 'player':
			action.append('PLYR:{}'.format(obj['val']))
		else:
			raise Exception('cant handle: {}'.format(repr(obj)))
	
	return ' '.join(map(str,action))
	
def _find_action(action, options):

	action = tuple(action)
	outs = [_package_action(a) for a in options]
	
	for o, full in zip(outs, options):
		if action == tuple(o):
			return full
	raise Exception('couldnt find: {}'.format(action))

def _package_action(action):
	
	final = []
	
	for obj in action:
		
		if obj['type'] == 'fixed':
			final.append(obj['val'])
		elif obj['type'] == 'obj':
			final.append(obj['ID'])
		elif obj['type'] == 'player':
			final.append(obj['val'])
		else:
			raise Exception('cant handle: {}'.format(repr(obj)))

	return list(final)

class Ipython_Runner(object):
	def __init__(self, addr, *users, seed=None, full_log=False, god_mode=False):
		self.addr = addr
		self.full_log = full_log
		self.god_mode = god_mode
		
		self.rng = RandomGenerator()
		if seed is None:
			seed = random.getrandbits(64)
		self.rng.seed(seed)
		self.seed = seed
		
		self.in_progress = False
		self.msg = None
		self.log = None
		self.key = None
		self.actions = None
		self.users = tdeque(users)
		self.user2players = tdict()
		self.players = tdict()
		self.specs = tset()
		
	def restart(self, debug=False):
		debug = 1 if debug else 0
		return send_http(self.addr, 'restart', debug)
		
	def _execute(self, *args, **kwargs):
		msg = send_http(self.addr, *args, **kwargs)
		if 'error' in msg:
			if isinstance(msg, dict):
				self.print_error(msg['error'])
			else:
				print(type(msg), msg)
			assert False
		return msg
		
	def print_error(self, error):
		print('*** ERROR: {} ***'.format(error['type']))
		print(error['msg'])
		print('****************************')
	
	def available_games(self):
		return self._execute('game/available')
	
	def select_game(self, name):
		return self._execute('game/select', name)
	
	def game_info(self):
		return self._execute('game/info')
	
	def game_players(self):
		return self._execute('game/players')
	
	def add_client(self, *users, port=None, interface=None, agent_type=None, timeout=5, **settings):
		
		data = r'http://localhost:{}/'.format(port) if port is not None else None
		
		if agent_type is not None:
			assert data is None
			data = {'agent_type':agent_type, 'timeout':timeout}
			data.update(settings)
			
		
		msg = ('add', 'client', users) if interface is None else ('add', 'client', interface, users)
		
		return self._execute(*msg, data=data)
	
	def go(self, user=None):
		if user is not None:
			return self._execute('continue', user)
		return self._execute('continue')
	
	def toggle_pause(self):
		return self._execute('autopause')
	
	def ping(self):
		return self._execute('ping', 'clients')
	
	def add_player(self, user=None, player=None):
		if user is None:
			user = self.users[0]
		assert player is not None # TODO maybe automatically load available players
		self.user2players[user] = player
		self.players[player] = user
		return self._execute('add/player', user, player)
	
	def add_advisor(self, user=None, player=None):
		if user is None:
			user = self.users[0]
		assert player is not None # TODO maybe automatically load available players
		return self._execute('add/advisor', user, player)
	
	def add_spectator(self, user=None):
		if user is None:
			user = self.users[0]
		self.specs.add(user)
		return self._execute('add/spectator', user)
	
	def auto_user(self, user=None):
		if user is None and self.msg is not None and 'waiting_for' in self.msg:
			user = self.players[next(iter(self.msg.waiting_for))]
		if user in self.users:
			self.users.remove(user)
		if user is not None:
			self.users.appendleft(user)
			print(f'Auto user: {user}')
	
	def set_user(self, user=None):
		if user is not None:
			try:
				self.users.remove(user)
			except:
				pass
			self.users.appendleft(user)
		else:
			self.users.append(self.users.popleft())
		print('set user: {}'.format(self.users[0]))
	
	def get_active_players(self):
		return self._execute('active')
	
	def get_roles(self):
		return self._execute('roles')
	
	def begin(self, seed=None):
		if seed is None:
			seed = self.seed
		self.in_progress = True
		return self._execute('begin', seed)
	
	def cheat(self, code=None):
		if code is None:
			return send_http(self.addr, 'cheat')
		return self._execute('cheat', code)
	
	def status(self, user=None):
		if user is None:
			user = self.users[0]
		self.msg = unjsonify(self._execute('status', user))
		self.key = self.msg.key if 'key' in self.msg else None
		
		if isinstance(self.msg, str):
			print('Error: {}'.format(self.msg))
		
		self._process_msg()
		
		return self.msg
	
	def step(self, idx=None, user=None):
		if user is None:
			user = self.users[0]
		
		group, action = self._select_action() if idx is None else self.actions[idx]
		
		action = _package_action(action)
		
		assert self.key is not None
		
		self.msg = unjsonify(self._execute('action', user, self.key, group, action))
		
		if isinstance(self.msg, str):
			print('Error: {}'.format(self.msg))
		
		self.actions = None
		self.key = None
		self._process_msg()
	
	def get_log(self, user=None, god=None):
		if user is None:
			user = self.users[0]
		if god is None:
			god = self.god_mode
		self.log = self._execute('log', user, 'true') if god else self._execute('log', user)
		return unjsonify(self.log)
	
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
		
		if self.full_log or 'log' in self.msg:
			print('-------------')
			print('Log')
			print('-------------')
			if self.full_log:
				print(_format_log(self.get_log()))  # TODO: make the same player is called
			elif 'log' in self.msg:
				print(_format_log(self.msg.log))
		
		if 'error' in self.msg:
			self.print_error(self.msg.error)
		
		if 'phase' in self.msg:
			print('Phase: {}'.format(self.msg.phase))
		
		
		
		if 'waiting_for' in self.msg:
			print('Waiting for: {}'.format(', '.join(self.msg.waiting_for)))
		elif 'end' in self.msg:
			print('--- Game Ended ---')
		else:
			
			if 'advice' in self.msg:
				advice = []
				for adv in self.msg.advice:
					action = _find_action(adv.action, decode_action_set(self.msg.options[adv.group].actions))
					# action = tuple(adv.action) # TODO: find correctly formatted action
					advice.append('{} recommends: {} - {}'.format(adv.user, adv.group, _format_action(action)))
				print('Advice:')
				print('\n'.join(advice))
			
			if 'status' in self.msg:
				status = _format_line(self.msg.status['line'])
				print('+' + '-' * (len(status) + 2) + '+')
				print('| {} |'.format(status))
				print('+' + '-' * (len(status) + 2) + '+')
			
			# print('Status: {}'.format(_format_line(self.msg.status)))
			else:
				print('No status found')
			
			if 'options' in self.msg:
				idx = 0
				
				for name, opt in self.msg.options.items():
					
					if 'desc' in opt:
						print('-- {} : {} --'.format(name, _format_line(opt.desc['line'])))
					
					for tpl in decode_action_set(opt.actions):
						print('{:>4} - {}'.format(idx, _format_action(tpl)))
						idx += 1
			
			else:
				print('Active: {}'.format(', '.join(self.get_active_players())))
	
	def _select_action(self):
		idx = self.rng.randint(0,len(self.actions)-1)
		return self.actions[idx]
	
	def _process_msg(self):
		
		if 'error' in self.msg:
			print('*** ERROR: {} ***'.format(self.msg.error.type))
			print(self.msg.error.msg)
			print('****************************')
		
		if 'end' in self.msg:
			self.in_progress = False
		
		if 'options' in self.msg:
			self.actions = tlist()
			for name, opts in self.msg.options.items():
				self.actions.extend((name, action) for action in decode_action_set(opts.actions))
		
		if 'key' in self.msg:
			self.key = self.msg.key
	

	def save(self, name, overwrite=True):
		if overwrite:
			return self._execute('save', name, 'true')
		return self._execute('save', name)
	
	def load(self, name, load_interface=False):
		if not load_interface:
			return self._execute('load', name, 'false')
		return self._execute('load', name)

#
# class Ipython_Interface(object):
#
# 	def __init__(self, controller, seed=None, full_log=False):
# 		super().__init__()
#
# 		self.ctrl = controller
# 		self.in_progress = False
#
# 		self.msg = None
# 		self.table = None
# 		if seed is None:
# 			seed = random.getrandbits(64)
# 		self.rng = random.Random(seed)
# 		self.seed = seed
# 		self.full_log = full_log
#
# 		self.actions = None
# 		self.action = None
#
# 		self.waiting_for = None
#
# 		self.player = None
# 		self.key = None
#
# 	def save(self, filename=None):
# 		data = self.ctrl.save()
# 		if filename is not None:
# 			pickle.dump(data, open(filename, 'wb'))
# 		else:
# 			return data
#
# 	def load(self, data):
# 		if isinstance(data, str):
# 			data = pickle.load(open(data, 'rb'))
# 		return self.ctrl.load(data)
#
# 	def set_player(self, player=None):
#
# 		if player is None:
# 			if self.msg is None:
# 				player = self.rng.choice(self.get_players())
# 			elif 'waiting_for' not in self.msg:
# 				print('Player set to {}'.format(self.player))
# 				return
# 			else:
# 				player = self.msg.waiting_for.pop()
#
# 		self.player = player
# 		print('Player set to {}'.format(self.player))
#
# 	def get_player(self, player=None):
# 		if player is None:
# 			player = self.player
# 		return _format(self.ctrl.get_player(player))
#
# 	def get_players(self):
# 		return _format(self.ctrl.get_players())
#
# 	def get_table(self, player=None):
# 		self.table = _format(self.ctrl.get_table(player=player))
#
# 	def get_obj_types(self):
# 		return _format(self.ctrl.get_obj_types())
#
# 	def get_log(self, player=None):
# 		if player is None:
# 			player = self.player
# 		return _format(self.ctrl.get_log(player))
#
# 	def get_IU_spec(self):
# 		return _format(self.ctrl.get_UI_spec())
#
# 	def get_status(self, player=None):
# 		if player is None:
# 			player = self.player
#
# 		self.msg = _format(self.ctrl.get_status(player))
#
# 		self._process_msg()
#
# 	def _process_msg(self):
#
# 		if 'error' in self.msg:
# 			print('*** ERROR: {} ***'.format(self.msg.error.type))
# 			print(self.msg.error.msg)
# 			print('****************************')
#
# 		if 'end' in self.msg:
# 			self.in_progress = False
#
# 		if 'options' in self.msg:
# 			self.actions = tlist()
#
# 			self.in_progress = True
#
# 			for opt in self.msg.options:
# 				self.actions.extend(decode_action_set(opt.actions))
#
# 		if 'key' in self.msg:
# 			self.key = self.msg.key
#
# 		if 'table' in self.msg:
# 			self.table = self.msg.table
#
# 		if 'players' in self.msg:
# 			self.players = self.msg.players
#
# 		if 'phase' in self.msg:
# 			self.phase = self.msg.phase
#
# 		# if 'waiting_for' in self.msg:
# 		# 	print('Waiting for: {}'.format(', '.join(self.msg.waiting_for)))
#
# 	def reset(self, player=None, seed=None):
# 		if player is None:
# 			player = self.player
# 		self.msg = _format(self.ctrl.reset(player=player, seed=seed))
#
# 		self._process_msg()
#
#
# 	def view(self):
# 		if self.msg is None:
# 			print('No message found')
# 			return
#
# 		if 'info' in self.msg:
# 			print('Received info: {}'.format(list(self.msg.info.keys())))
#
# 		if 'key' in self.msg:
# 			print('Received key: {}'.format(self.msg.key))
#
# 		if 'table' in self.msg:
# 			print('Received table: {} entries'.format(len(self.msg.table)))
#
# 		if self.full_log or 'log' in self.msg:
# 			print('-------------')
# 			print('Log')
# 			print('-------------')
# 			if self.full_log:
# 				print(_format_log(self.get_log())) # TODO: make the same player is called
# 			elif 'log' in self.msg:
# 				print(_format_log(self.msg.log))
#
# 		if 'error' in self.msg:
# 			print('*** ERROR: {} ***'.format(self.msg.error.type))
# 			print(self.msg.error.msg)
# 			print('****************************')
#
# 		if 'phase' in self.msg:
# 			print('Phase: {}'.format(self.msg.phase))
#
# 		if 'waiting_for' in self.msg:
# 			print('Waiting for: {}'.format(', '.join(self.msg.waiting_for)))
# 		elif 'end' in self.msg:
# 			print('--- Game Ended ---')
# 		else:
#
# 			if 'status' in self.msg:
# 				status = _format_line(self.msg.status['line'])
# 				print('+' + '-' * (len(status) + 2) + '+')
# 				print('| {} |'.format(status))
# 				print('+' + '-' * (len(status) + 2) + '+')
#
# 				# print('Status: {}'.format(_format_line(self.msg.status)))
# 			else:
# 				print('No status found')
#
# 			if 'options' in self.msg:
# 				idx = 0
#
# 				for opt in self.msg.options:
#
# 					if 'desc' in opt:
# 						print('-- {} --'.format(_format_line(opt.desc['line'])))
#
# 					for tpl in decode_action_set(opt.actions):
# 						print('{:>4} - {}'.format(idx, _format_action(tpl)))
# 						idx += 1
#
#
#
# 	def view_info(self):
# 		if self.msg is None or 'info' not in self.msg:
# 			print('No info to print')
# 		return render_dict(self.msg.info)
#
# 	def view_table(self):
# 		if self.table is None:
# 			print('No table to print')
#
# 		return render_dict(self.table)
#
# 	def select_action(self, idx=None):
#
# 		if self.actions is None or not len(self.actions):
# 			print('No actions to select')
# 			return
#
# 		if idx is None:
# 			idx = self.rng.randint(0,len(self.actions)-1)
#
# 		self.action = self.actions[idx]
#
# 		print('Selected action {}: {}'.format(idx, _format_action(self.action)))
#
#
# 	def step(self):
#
# 		if not self.in_progress:
# 			print('No game in progress')
# 			return
#
# 		if self.action is None:
# 			print('Must first select an action')
# 			return
#
# 		if self.key is None:
# 			print('No key found')
# 			return
#
# 		self.msg = _format(self.ctrl.step(player=self.player, action=_package_action(self.action), key=self.key))
#
# 		self.key = None
#
# 		self._process_msg()
#
# 		self.action = None
# 		self.actions = None
#








def render_format(raw, unfolded=False):
	
	if isinstance(raw, Jsonable) and unfolded:
		return raw.jsonify()
	unfolded = True
	if isinstance(raw, set):
		itr = dict()
		for i, el in enumerate(raw):
			itr['s{}'.format(i)] = render_format(el, unfolded)
		return itr
	elif isinstance(raw, dict):
		return dict((str(k), render_format(v, unfolded)) for k, v in raw.items())
	elif isinstance(raw, GameObject):
		return {k:render_format(raw[k], unfolded) for k in raw}
	elif isinstance(raw, list):
		# return list(render_format(el) for el in raw)
		itr = dict()
		for i, el in enumerate(raw):
			itr['l{}'.format(i)] = render_format(el, unfolded)
		return itr
	elif isinstance(raw, tuple):
		# return list(render_format(el) for el in raw)
		itr = dict()
		for i, el in enumerate(raw):
			itr['t{}'.format(i)] = render_format(el, unfolded)
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
		
		
		
