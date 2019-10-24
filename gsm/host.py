
import pickle
import yaml
import json
from collections import OrderedDict
from .mixins import Named
from .signals import InvalidValueError, RegistryCollisionError, NoActiveGameError, UnknownGameError, LoadConsistencyError, UnknownInterfaceError, UnknownPlayerError, UnknownUserError

_game_registry = {}
def register_game(name, cls, path=None):
	if name in _game_registry:
		raise RegistryCollisionError(name)
	info = path if path is None else yaml.load(open(path, 'r'))
	_game_registry[name] = cls, info


_interface_registry = {}
def register_interface(name, cls):
	if name in _interface_registry:
		raise RegistryCollisionError(name)
	_interface_registry[name] = cls
def get_interface(name):
	if name not in _interface_registry:
		raise InvalidValueError(name)
	return _interface_registry[name]

class Interface(Named, object):
	
	def ping(self):
		return 'ping reply'
	
	def reset(self, user):
		return 'Interface Reset'
	
	def step(self, user, msg):
		raise NotImplementedError

class Test_Interface(Interface):
	def __init__(self):
		super().__init__('Test')
	
	def ping(self):
		print('ping')
		return 'ping reply'
	
	def reset(self, user):
		print('reset')
		return 'Interface Reset'
		
	def step(self, user, msg):
		print('step')
		print(msg)
		return 'nothing'
		
register_interface('test', Test_Interface)

class Host(object):
	def __init__(self, seed=None):
		super().__init__()
		
		self.seed = seed
		self._in_progress = False
		self.game = None
		self.ctrl_cls = None
		self.ctrl = None
		self.info = None
		
		self.settings = {}
		
		self.roles = OrderedDict()
		self.players = OrderedDict()
		self.users = set()
		
		self.interfaces = OrderedDict()
		
		self.advisors = OrderedDict()
		self.spectators = set()
		
	def get_available_games(self):
		return list(_game_registry.keys())
		
	def get_game_info(self, name):
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
	
	def add_passive_client(self, address, *users):
		for user in users:
			self.interfaces[user] = address
			self.users.add(user)
		
	def add_spectator(self, user, advisor=None):
		self.users.add(user)
		if advisor is not None:
			self.advisors[user] = advisor
		else:
			self.spectators.add(user)
	
	def add_player(self, user, player):
		self.players[player] = user
		self.roles[user] = player
		self.users.add(user)
		
	def begin_game(self):
		if self.ctrl_cls is None:
			raise Exception('Must set a game first')
		if len(self.players) not in self.info.num_players:
			raise Exception('Invalid number of players {}, allowed for {}: {}'.format(len(self.players), self.info.name, ', '.join(self.info.num_players)))
		
		player = next(iter(self.players.keys()))
		
		self.ctrl = self.ctrl_cls(**self.settings)
		self.ctrl.reset(player, seed=self.seed)
	
	def reset(self):
		self.ctrl = None
		self.settings.clear()
	
	def set_setting(self, key, value):
		self.settings[key] = value
	def del_setting(self, key):
		del self.settings[key]
	
	def save_game(self, path, fixed_users=False):
		if self.ctrl is None:
			raise NoActiveGameError
		state = self.ctrl.save()
		data = {'state':state, 'players':self.players}
		if fixed_users:
			data['fixed_users'] = True
		
		pickle.dump(data, open(path, 'wb'))
	
	def load_game(self, path):
		if self.ctrl is None:
			raise NoActiveGameError
		
		data = pickle.load(open(path, 'rb'))
		
		if 'fixed_users' in data:
			for player, user in data['players'].items():
				if player not in self.players or self.players[player] != user:
					raise LoadConsistencyError
				
		self.ctrl.load(data)
	
	def take_action(self, user, action, key):
		if user not in self.roles:
			raise UnknownUserError
		player = self.roles[user]
		msg = self.ctrl.step(player, action, key)
		
		if self._active_backend_step():
			msg = self.ctrl.get_status(player)
		return msg
	
	def _active_backend_step(self):
		
		all_passive = False
		recheck = False
		while not all_passive:
			all_passive = True
			players = json.loads(self.ctrl.get_active_players())
			for player in players:
				user = self.players[player]
				if user in self.interfaces:
					all_passive = False
					recheck = True
					interface = self.interfaces[user]
					interface(self.ctrl.get_status(player))
					break
		
		return recheck
	
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
	