import time
import pickle
import yaml
import json
from collections import OrderedDict
from ..mixins import Named
from ..signals import InvalidValueError, RegistryCollisionError, NoActiveGameError, UnknownGameError, LoadConsistencyError, UnknownInterfaceError, UnknownPlayerError, UnknownUserError
from .registry import _game_registry, get_trans
from .transmit import send_http

class Host(object):
	def __init__(self, address, debug=False, **settings):
		super().__init__()
		
		self._in_progress = False
		self.debug = debug
		self.game = None
		self.ctrl_cls = None
		self.ctrl = None
		self.info = None
		
		self.address = address
		self.settings = settings
		
		self.roles = OrderedDict()
		self.players = OrderedDict()
		self.users = set()
		
		self.interfaces = OrderedDict()
		
		self.advisors = OrderedDict()
		self.spectators = set()
		
		self.auto_pause = False
		
	def toggle_pause(self):
		self.auto_pause ^= True
		return 'auto pause is {}activated'.format('' if self.auto_pause else 'de')
		
	def continue_step(self, user=None):
		self._passive_frontend_step()
		if user is None:
			return 'continued'
		return self.get_status(user)
	
	def get_available_games(self):
		return list(_game_registry.keys())
		
	def get_available_players(self):
		all_players = list(self.get_game_info()['player_names'])
		for p in self.players:
			if p in all_players:
				all_players.remove(p)
		return all_players
		
	def get_game_info(self, name=None):
		if name is None:
			name = self.game
		if name not in _game_registry:
			raise UnknownGameError
		return _game_registry[name][1]
	
	def set_game(self, name):
		
		if name not in _game_registry:
			raise UnknownGameError
		
		cls, info = _game_registry[name]
		
		self.game = name
		self.info = info
		self.ctrl_cls = cls
	
	def add_passive_client(self, *users, address=None,
	                       interface=None, settings={}):
		
		if address is not None:
			assert interface is not None, 'must specify the interface to be used'
			trans = 'http'
			args = (address, self.address)
			settings = {}
		else:
			trans = 'proc'
			args = self.address, interface, *users
		
		interface = get_trans(trans)(*args, **settings)
		
		for user in users:
			self.interfaces[user] = interface
			self.users.add(user)
		
	def add_spectator(self, user, advisor=None):
		self.users.add(user)
		if advisor is not None:
			self.advisors[user] = advisor
			if advisor not in self.players:
				self.players[advisor] = []
			self.players[advisor].append(user)
			if user in self.interfaces:
				self.interfaces[user].set_player(user, advisor)
		else:
			self.spectators.add(user)
	
	def add_player(self, user, player):
		
		if player not in self.info['player_names']:
			return 'No player is called: {}'.format(player)
		
		if player not in self.players:
			self.players[player] = []
		self.players[player].append(user)
		self.roles[user] = player
		self.users.add(user)
		if user in self.interfaces:
			self.interfaces[user].set_player(user, player)
		
		return '{} is now playing {}'.format(user, player)
		
	def begin_game(self, seed=None):
		if self.ctrl_cls is None:
			raise Exception('Must set a game first')
		if len(self.players) not in self.info['num_players']:
			raise Exception('Invalid number of players {}, allowed for {}: {}'.format(len(self.players), self.info.name, ', '.join(self.info.num_players)))
		
		for user, interface in self.interfaces.items():
			interface.reset(user)
		
		player = next(iter(self.players.keys()))
		
		self.ctrl = self.ctrl_cls(debug=self.debug, **self.settings)
		self.ctrl.reset(player, seed=seed)
		
		self._passive_frontend_step()
	
	def reset(self):
		self.ctrl = None
		self.settings.clear()
	
	def set_setting(self, key, value):
		self.settings[key] = value
	def del_setting(self, key):
		del self.settings[key]
	
	def cheat(self, code=None):
		self.ctrl.cheat(code)
		return 'Cheat code: {}'.format(code)
	
	def save_game(self, path, fixed_users=False):
		if self.ctrl is None:
			raise NoActiveGameError
		state = self.ctrl.save()
		data = {'state':state, 'players': self.players}
		if fixed_users:
			data['fixed_users'] = True
		
		pickle.dump(data, open(path, 'wb'))
	
	def load_game(self, path):
		if self.ctrl is None:
			raise NoActiveGameError
		
		data = pickle.load(open(path, 'rb'))
		
		# if 'fixed_users' in data:
		# 	for player, user in data['players'].items():
		# 		if player not in self.players or self.players[player] != user:
		# 			raise LoadConsistencyError
				
		self.ctrl.load(data)
	
	def take_action(self, user, group, action, key):
		if user not in self.roles:
			raise UnknownUserError
		player = self.roles[user]
		msg = self.ctrl.step(player, group, action, key)
		
		out = json.loads(msg)
		if 'error' in out:
			return msg
		
		if self._passive_frontend_step():
			msg = self.ctrl.get_status(player)
		return msg
	
	def give_advice(self, user, group, action):
		if user not in self.advisors:
			raise UnknownUserError
		player = self.advisors[user]
		self.ctrl.give_advice(player, group=group, action=action, user=user)
		return 'Advice for {} is posted'.format(player)
	
	def _passive_frontend_step(self):
		
		no_passive = False
		recheck = False
		first = True
		
		advised = set()
		
		while not no_passive:
			no_passive = True
			players = json.loads(self.ctrl.get_active_players())
			
			if self.auto_pause and not first:
				return recheck
			for player in players:
				for user in self.players[player]:
					if user in self.interfaces and user not in advised:
						no_passive = False
						
						if user in self.roles:
							status = self.ctrl.get_status(player)
						else:
							status = self.ctrl.get_advisor_status(player)
							advised.add(user)
						
						status = json.loads(status)
						
						if 'options' in status:
							msg = json.loads(self.interfaces[user].step(user, status))
						else:
							msg = None
						
						if msg is None:
							return recheck
						elif 'key' in msg: # TODO: enable spectator/advisor handling
							self.ctrl.step(player, group=msg['group'], action=msg['action'], key=msg['key'])
							recheck = True
						elif 'action' in msg:
							self.give_advice(user, group=msg['group'], action=msg['action'])
							recheck = True
						elif 'error' in msg:
							print('Error: {}'.format(msg))
						else:
							no_passive = True
						break
			first = False
		
		return recheck
	
	def ping_interfaces(self):
		pings = {}
		for user, interface in self.interfaces.items():
			start = time.time()
			response = interface.ping() # TODO: check to make sure theres no timeout
			pings[user] = response, time.time() - start
		return json.dumps(pings)
	
	def get_status(self, user):
		if self.ctrl is None:
			raise NoActiveGameError
		if user in self.spectators:
			return self.ctrl.get_spectator_status()
		if user in self.advisors:
			player = self.advisors[user]
			return self.ctrl.get_advisor_status(player)
		if user not in self.roles:
			raise UnknownUserError
		player = self.roles[user]
		return self.ctrl.get_status(player)
	
	def get_player(self, user):
		if user not in self.users:
			raise InvalidValueError(user)
		if self.ctrl is None:
			raise NoActiveGameError
		player = self.roles[user]
		return self.ctrl.get_player(player)
		
	def get_table(self, user):
		if user not in self.roles:
			raise InvalidValueError(user)
		if self.ctrl is None:
			raise NoActiveGameError
		player = self.roles[user]
		return self.ctrl.get_table(player)
	
	def get_log(self, user):
		if user not in self.roles:
			raise InvalidValueError(user)
		if self.ctrl is None:
			raise NoActiveGameError
		player = self.roles[user]
		return self.ctrl.get_log(player)
	
	def get_obj_types(self):
		if self.ctrl is None:
			raise NoActiveGameError
		return self.ctrl.get_obj_types()
	