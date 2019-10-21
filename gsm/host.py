
import pickle
import yaml
import json
from collections import OrderedDict
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

class Interface(object):
	
	def ping(self):
		return 'ping reply'
	
	def reset(self):
		return
	
	def step(self, msg):
		raise NotImplementedError

class Test_Interface(Interface):
	
	def ping(self):
		print('ping')
		return 'ping reply'
	
	def reset(self):
		print('reset')
		
	def step(self, msg):
		print('step')
		print(msg)
		
register_interface('test', Test_Interface)

class Host(object):
	def __init__(self, seed=None):
		super().__init__()
		
		self.seed = seed
		self._in_progress = False
		self.ctrl = None
		self.info = None
		
		self.roles = OrderedDict()
		self.players = OrderedDict()
		self.users = set()
		
		self.interfaces = OrderedDict()
		
		self.advisors = OrderedDict()
		self.spectators = set()
		
	def get_game_info(self, name):
		if name not in _game_registry:
			raise UnknownGameError
		return _game_registry[name][1]
	
	def set_game(self, name, **settings):
		
		if name not in _game_registry:
			raise UnknownGameError
		
		cls, info = _game_registry[name]
		
		self.info = info
		self.ctrl = cls(**settings)
		
	
	def add_active_client(self, interface, *users):
		assert interface.is_active(), 'Can only add active clients (passive clients can join directly)'
		for user in users:
			self.interfaces[user] = interface
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
		if self.ctrl is None:
			raise Exception('Must set a game first')
		if len(self.players) not in self.info.num_players:
			raise Exception('Invalid number of players {}, allowed for {}: {}'.format(len(self.players), self.info.name, ', '.join(self.info.num_players)))
		
		player = next(iter(self.players.keys()))
		
		msg = self.ctrl.reset(player, seed=self.seed)
		
		raise NotImplementedError
	
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
	