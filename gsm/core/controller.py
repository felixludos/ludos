
import sys, os
import json
import random
import traceback
import inspect
import yaml

from humpack import tset, tdict, tlist, containerify
from humpack import pack_member, unpack_member, json_pack, json_unpack
from .logging import GameLogger
from .state import GameState, GameData
from .table import GameTable
from .player import GameManager
from .phase import GameStack
from ..mixins import Named, Transactionable, Packable
from ..signals import _PhaseControl, PhaseComplete, SwitchPhase, GameOver
from ..errors import InvalidPlayerError, NoActiveGameError, InvalidKeyError, ClosedRegistryError, RegistryCollisionError
from ..errors import ResolutionError, MissingValueError, MissingObjectError, NoPlayersFoundError
from ..util import RandomGenerator, jsonify, get_printer
from ..io.registry import Game

from ..io import register_game

prt = get_printer(__name__)

class GameController(Named, Transactionable, Packable):
	
	def __init_subclass__(cls, register=True, name=None, info_path=None, **kwargs):
		super().__init_subclass__(**kwargs)
		
		cls.__home__ = os.path.dirname(inspect.getfile(cls))
		cls.config_files = tdict()
		
		config_dir = os.path.join(cls.__home__, 'config')
		
		if os.path.isdir(config_dir):
			prt.info(f'Config dir found for {cls.__name__} at {config_dir}')
			
			for fname in os.listdir(config_dir):
				name = fname.split('.')[0]
				path = os.path.join(config_dir, fname)
				cls.register_config(name, path)
			
		if register:
			Game(name=name, info_path=info_path)(cls)
			
	@classmethod
	def register_config(cls, name, path):
		if name in cls.config_files:
			prt.warning(f'Config file with name {name} is already registered in {cls.__name__}')
			
		cls.config_files[name] = path
	
	@classmethod
	def load_configs(cls):
		config = tdict()
		
		for name, path in cls.config_files.items():
			config[name] = containerify(yaml.load(open(path, 'r')))
		
		return config
	
	@classmethod
	def _view_info(cls):
		return cls.info.copy()
	
	@classmethod
	def choose_table(cls):
		return cls._choose_obj('objects', '_req_table', GameTable)
	@classmethod
	def choose_stack(cls):
		return cls._choose_obj('phases', '_req_stack', GameStack)
	@classmethod
	def choose_manager(cls):
		return cls._choose_obj('player_types', '_req_manager', GameManager)
	
	@classmethod
	def _choose_obj(cls, key, attr, default):
		
		game_info = cls.info
		
		if key not in game_info:
			return default
		
		reqs = []
		for name, obj in game_info[key].items():
			if 'cls' in obj:
				obj = obj['cls']
				req = getattr(obj, attr, None)
				if req is not None:
					reqs.append(req)
		
		if len(reqs) == 0:
			return default
		
		for req in reqs:
			for parent in reqs:
				if req not in parent.__mro__:
					break
			else:
				return req
		
		raise ResolutionError(reqs)
	
	def __new__(cls, *args, **kwargs):
		new = super().__new__(cls)
		
		# meta values (neither for dev nor user) (not including soft registries - they dont change)
		new._tmembers = {'state', 'log', 'table', 'stack', 'manager', 'end_info', '_advice', 'active_players',
		                 'keys', 'RNG', '_key_rng', '_images', '_advisor_images', 'config'}
		return new
	
	def __init__(self, name=None, debug=False,
	             manager=None, stack=None, table=None, log=None,
	             **settings):
		if name is None:
			# TODO: add suggestion about game name
			name = self.__class__.__name__
		super().__init__(name)

		if manager is None:
			manager = self.choose_manager()()
		if stack is None:
			stack = self.choose_stack()()
		if table is None:
			table = self.choose_table()()
		if log is None:
			log = GameLogger()
		
		game_info = self._view_info()
		
		# Registries and managers
		self.stack = stack
		self.stack.populate(game_info['phases'])
		self.table = table
		self.table.populate(game_info['objects'])
		self.manager = manager # manager gets populated in reset()
		
		self.config_files = tdict()
		
		# GameState
		self._in_progress = False # flag for registration to end
		self._in_transaction = False # flag for transactionable
		self.DEBUG = debug # flag for dev to use as needed
		
		self.keys = tdict() # a one time permission to call step() (with a valid action)
		self.RNG = RandomGenerator()
		self._images = tdict()
		self._advice = tdict()
		self._advisor_images = tdict()
		self._spec_image = None
		
		self.state = None
		self.active_players = None
		self.settings = containerify(settings)
		self.config = self.load_configs()
		self.end_info = None
		
		# Game components
		self.log = log
		
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
		
		self._in_transaction = True
		for mem in self._tmembers:
			obj = self.__dict__[mem]
			if obj is not None:
				obj.begin()
		
	
	def in_transaction(self):
		return self._in_transaction
	
	def commit(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		for mem in self._tmembers:
			obj = self.__dict__[mem]
			if obj is not None:
				obj.commit()
		
	
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		for mem in self._tmembers:
			obj = self.__dict__[mem]
			if obj is not None:
				obj.abort()
		
	
	def __pack__(self):
		
		data = {}
		
		# registries
		data['config_files'] = pack_member(self.config_files)
		
		# tmembers - arbitrary Packable instances
		for mem in self._tmembers:
			data[mem] = pack_member(self.__dict__[mem])
		
		data['name'] = pack_member(self.name)
		data['_in_progress'] = pack_member(self._in_progress)
		data['_in_transaction'] = pack_member(self._in_transaction)
		data['_pre_setup_complete'] = pack_member(self._pre_setup_complete)
		data['_spec_image'] = pack_member(self._spec_image)
		data['debug'] = pack_member(self.DEBUG)
		data['active_players'] = pack_member(self.active_players)
		
		return data
	
	def __unpack__(self, data):
		
		# load registries
		self.config_files = unpack_member(data['config_files'])
		
		# unpack tmembers
		for mem in self._tmembers:
			self.__dict__[mem] = unpack_member(data[mem])
			
		self.name = unpack_member(data['name'])
		self._in_transaction = unpack_member(data['_in_transaction'])
		self._in_progress = unpack_member(data['_in_progress'])
		self._pre_setup_complete = unpack_member(data['_pre_setup_complete'])
		self._spec_image = unpack_member(data['_spec_image'])
		self.DEBUG = unpack_member(data['debug'])
		self.active_players = unpack_member(data['active_players'])
	
	######################
	# Do NOT Override
	######################
		
	def _reset(self, player, seed=None):
		
		# reset all components
		if seed is None:
			seed = random.getrandbits(64)
		self.seed = seed

		self._key_rng = RandomGenerator(self.seed)
		self.RNG = RandomGenerator(self.seed)
		
		self.end_info = None
		self.active_players = tdict()
		
		# init components
		self.state = GameState()
		self.manager.reset(self)
		self._add_players(self.config, self.settings)
		self.log.reset(self)  # TODO: maybe this shouldnt just be the names
		self.table.reset(self)
		self.stack.reset(self)
		
		# init game
		data = self._get_data()
		data.lock()
		
		self._init_game(data, self.config, self.settings)  # builds maps/objects
		self._in_progress = True
		
		# create starting phase
		self._create_start_phase(data, self.config, self.settings)
		
		# execute first player
		return self._step(player)
	
	def _step(self, player, group=None, action=None, key=None):  # returns python objs (but json readable)
		
		try:
			if player in self.manager:
				player = self.manager[player]
			else:
				raise InvalidPlayerError(player)
			
			if not len(self.stack):
				raise GameOver
			
			if self.active_players is None:
				raise NoActiveGameError('Call reset() first')
			
			if action is not None:
				if player not in self.active_players:
					return self._compose_msg(player)
				
				if key is None or key != self.keys[player]:
					raise InvalidKeyError
				
				action = self.active_players[player].verify(group, action) # action is a tuple with (action-group, (action-tuple))
			
			# start transaction
			self.begin()
			
			# prepare executing actions - collect game data
			data = self._get_data()
			data.lock()
			
			# execute action
			while len(self.stack):
				phase = self.stack.pop()
				try:
					phase.execute(data, player=player, action=action)
					# get next action
					out = phase.encode(data)
				except PhaseComplete as intr:
					if not intr.transfer_action():
						action = None
				except _PhaseControl as intr:
					if intr.stacks():
						self.stack.push(phase)  # keep current phase around
					new = intr.get_phase()
					self.stack.push(new, **intr.get_phase_kwargs())
					if not intr.transfer_action():
						action = None
				else: # successfully took a step and generated current action sets
					self.stack.push(phase)
					break
			
			if not len(self.stack): # ran out of phases, so game must be over. This probably shouldn't happen, instead raise a GameOver signal manually in the phase
				raise GameOver
		
		except GameOver:
			self.commit()
			
			if self.end_info is None:
				self._clear_images()
				data = self._get_data()
				data.lock()
				self.end_info = self._end_game(data)
				self._in_progress = False
			
			msg = self._compose_msg(player)
		
		except Exception as e:
			self.abort()
			# error handling
			
			msg = {
				'error': {
					'type': e.__class__.__name__,
					'msg': ''.join(traceback.format_exception(*sys.exc_info())),
				},
			}
		
		else:
			self.commit()
			# format output message
			
			self.active_players = tdict({p.name:opts for p, opts in out.items()})
			
			self._clear_images()
			
			msg = self._compose_msg(player)
		
		return msg
	
	######################
	# Must be Overridden
	######################
	
	# This function is implemented by dev to initialize the gamestate, and define player order
	def _init_game(self, C, config, settings):
		raise NotImplementedError
	
	def _end_game(self, C): # return info to be sent at the end of the game
		raise NotImplementedError
	
	######################
	# Optionally Overridden
	######################
	
	def _create_start_phase(self, C, config, settings, **kwargs):
		self.stack.push(self.stack._start_phase, **kwargs)
	
	def _add_players(self, config, settings,
	                 player_names=None, player_info=None, shuffle_order=None):
		
		game_info = self._view_info()
		
		if player_names is None:
			if 'player_names' in settings:
				player_names = settings['player_names']
			elif 'player_names' in game_info:
				player_names = game_info['player_names']
			else:
				raise NoPlayersFoundError()
		
		if shuffle_order is None:
			if 'shuffle_order' in settings:
				shuffle_order = settings['shuffle_order']
			elif 'shuffle_order' in game_info:
				shuffle_order = game_info['shuffle_order']
			else:
				shuffle_order = False
			
		
		if player_info is None:
			if 'player_info' in game_info:
				player_info = game_info['player_info']
			else:
				player_info = [{} for _ in player_names]
			
			assert len(player_info) == len(player_names), 'number of player_info doesnt match player_names: ' \
			                                              f'{len(player_names)} vs {len(player_info)}'
			
			if 'player_info' in settings: # TODO: include option to shuffle player order
				for info, new in zip(player_info, settings['player_info']):
					info.update(new)
		
		player_info = dict(zip(player_names, player_info))
		if shuffle_order:
			self.RNG.shuffle(player_names)
		
		for name in player_names:
			self.manager.create(name, **player_info[name])
		
	def cheat(self, code=None):
		pass
	
	def _clear_images(self):
		self._images.clear()
		self._advisor_images.clear()
		self._advice.clear()
		self._spec_image = None
	
	def _gen_key(self, player=None):
		key = hex(self._key_rng.getrandbits(64))[2:]
		if player is not None:
			self.keys[player] = key
		return key
	
	def _extra_game_data(self):
		return {}
	
	def _compose_msg(self, player=None, advisor=False):
		
		if player in self._images and not advisor:
			msg = json.loads(self._images[player])
		else:
			if self.end_info is not None:
				# game is already over
				msg = {
					'end': jsonify(self.end_info),
					'table': self.table.pull(), # full table
				}
			else:
				if player in self.active_players:
					msg = self.active_players[player].pull()
					if not advisor:
						msg['key'] = self._gen_key(player)
				elif player is not None:
					msg = {'waiting_for': list(self.active_players.keys())}
				else:
					msg = {}
				
				msg['players'] = self.manager.pull(player)
				msg['table'] = self.table.pull(player)
				msg['phase'] = self.stack.peek().get_name()
				
			msg['log'] = self.log.pull(player)
			# log = self.log.pull(player)
			# if len(log):
			# 	msg['log'] = log
			
		if not advisor and player in self._advice:
			if 'advice' not in msg:
				msg['advice'] = []
			msg['advice'].extend(self._advice[player])
			del self._advice[player]
		
		if player is not None:
			if advisor:
				self._advisor_images[player] = json.dumps(msg)
			else:
				self._images[player] = json.dumps(msg)
		else:
			self._spec_image = json.dumps(msg)
		
		return msg
	
	def _get_data(self):
		return GameData(
			state = self.state,
			
			log = self.log,
			players = self.manager,
			table = self.table,
			stack = self.stack,
			
			RNG = self.RNG,
			
			create_object = self.table.create,
		)
	
	######################
	# User functions (return json str)
	######################
	
	def step(self, player, group=None, action=None, key=None):  # returns json bytes (str)
		return json.dumps(self._step(player=player, group=group, action=action, key=key))
	
	def give_advice(self, player, group, action, **info):
		if player not in self._advice:
			self._advice[player] = tlist()
			
		advice = info
		advice.update({'group':group, 'action':action})
		self._advice[player].append(advice)
	
	def reset(self, player, seed=None):
		return json.dumps(self._reset(player, seed))
	
	def get_status(self, player):
		if player not in self._images or player in self._advice:
			self._compose_msg(player)
		return self._images[player]
	
	def get_advisor_status(self, player):
		if player not in self._advisor_images:
			self._compose_msg(player, advisor=True)
		return self._advisor_images[player]
	
	def get_spectator_status(self):
		if self._spec_image is None:
			self._compose_msg()
		return self._spec_image
	
	def get_active_players(self):
		return json.dumps(list(self.active_players.keys()))
	
	def get_player(self, player):
		return json.dumps(jsonify(self.manager[player]))
	
	def get_players(self):
		return json.dumps(list(self.manager.names()))
	
	def get_table(self, player=None):
		return json.dumps(self.table.pull(player))
	
	def get_obj_types(self):
		return json.dumps(self.table.get_obj_types())
	
	def get_log(self, player=None, god_mode=False):
		log = self.log.get_full(player, god_mode)
		return json.dumps(jsonify(log))
	
	def get_UI_spec(self): # returns a specification for gUsIm - may be overridden to include extra data
		raise NotImplementedError # TODO: by default it should return contents of a config file
	
	def save(self):  # returns string
		data = json_pack(self)
		# data = str(Packable.pack(self))
		# print('key: {}'.format(self.RNG.random())) # testing
		return data
	
	def load(self, data):
		
		obj = json_unpack(data)
		
		# load registries
		self.config_files = obj.config_files
		
		# unpack tmembers
		for mem in self._tmembers:
			self.__dict__[mem] = obj.__dict__[mem]
		
		self.name = obj.name
		self._in_transaction = obj._in_transaction
		self._in_progress = obj._in_progress
		self.DEBUG = obj.DEBUG
	
	
	
	
	



