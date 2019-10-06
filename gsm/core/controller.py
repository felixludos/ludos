
import sys
import json
import random
import traceback
import yaml

from humpack import tset, tdict, tlist, containerify
from .logging import GameLogger
from .state import GameState
from .table import GameTable
from .player import GameManager
from ..mixins import Named, Transactionable, Savable
from ..signals import PhaseComplete, PhaseInterrupt, GameOver, NoActiveGameError, InvalidKeyError, ClosedRegistryError, RegistryCollisionError, MissingValueError, MissingObjectError
from ..util import RandomGenerator, jsonify, obj_jsonify

class GameController(Named, Transactionable, Savable):
	
	def __new__(cls, *args, **kwargs):
		new = super().__new__(cls)
		
		# meta values (neither for dev nor user) (not including soft registries - they dont change)
		new._tmembers = {'state', 'log', 'table', 'active_players', 'phase_stack', 'end_info',
		                 'keys', 'RNG', '_key_rng', '_images', 'players', 'config'}
		return new
	
	def __init__(self, name=None, debug=False, manager=None, **settings):
		if name is None:
			# TODO: add suggestion about game name
			name = self.__class__.__name__
		super().__init__(name)
		
		# Hard registries - include python classes (cant directly be saved)
		self._phases = tdict() # dict of phase classes
		
		if manager is None:
			manager = GameManager()
		
		# Soft registries - only information, but must be provided before game start
		self.players = manager
		self.config_files = tdict()
		
		# GameState
		self._in_progress = False # flag for registration to end
		self._in_transaction = False # flag for transactionable
		self.DEBUG = debug # flag for dev to use as needed
		
		self.keys = tdict() # a one time permission to call step() (with a valid action)
		self.RNG = RandomGenerator()
		self._images = tdict()
		
		self.state = None
		self.active_players = None
		self.config = tdict(settings=tdict(settings))
		self.end_info = None
		self.phase_stack = None # should only contain instances of GamePhase
		
		# Game components
		self.log = None
		self.table = GameTable() # needed to register obj_types
	
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
		
	
	def __save__(self):
		pack = self.__class__._pack_obj
		
		data = {}
		
		# registries
		data['_phases'] = pack(self._phases)
		data['players'] = pack(self.players)
		data['config_files'] = pack(self.config_files)
		
		# tmembers - arbitrary Savable instances
		for mem in self._tmembers:
			data[mem] = pack(self.__dict__[mem])
		
		data['name'] = pack(self.name)
		data['_in_progress'] = pack(self._in_progress)
		data['_in_transaction'] = pack(self._in_transaction)
		data['debug'] = pack(self.DEBUG)
		
		
		return data
	
	def __load__(self, data):
		unpack = self.__class__._unpack_obj
		
		# load registries
		self._phases = unpack(data['_phases'])
		self.players = unpack(data['players'])
		self.config_files = unpack(data['config_files'])
		
		# unpack tmembers
		for mem in self._tmembers:
			self.__dict__[mem] = unpack(data[mem])
			
		self.name = unpack(data['name'])
		self._in_transaction = unpack(data['_in_transaction'])
		self._in_progress = unpack(data['_in_progress'])
		self.DEBUG = unpack(data['debug'])
	
	
	
	######################
	# Registration
	######################
	
	def register_config(self, name, path):
		if self._in_progress:
			raise ClosedRegistryError
		# if name in self.config_files:
		# 	raise RegistryCollisionError(name)
		self.config_files[name] = path
	def register_obj_type(self, obj_cls=None, name=None, req=[], open=[]):
		if self._in_progress:
			raise ClosedRegistryError
		self.table.register_obj_type(obj_cls=obj_cls, name=name, req=req, open=open)
	def register_phase(self, cls, name=None):
		if self._in_progress:
			raise ClosedRegistryError
		if name is None:
			name = cls.__class__.__name__
		# if name in self._phases:
		# 	raise RegistryCollisionError(name)
		self._phases[name] = cls
	def register_player(self, name, **props):
		if self._in_progress:
			raise ClosedRegistryError
		self.players.register(name, **props)
	
	######################
	# Do NOT Override
	######################
		
	def _reset(self, player, seed=None):
		
		if seed is None:
			seed = random.getrandbits(64)
		
		self.seed = seed

		self._key_rng = RandomGenerator(self.seed)
		self.RNG = RandomGenerator(self.seed)
		
		self.config.update(self._load_config())
		
		self._pre_setup(self.config)
		
		self.end_info = None
		self.active_players = tdict()
		
		self.state = GameState()
		self.log = GameLogger(tset(self.players.names()))
		self.table.reset(tset(self.players.names()))
		
		self.phase_stack = self._set_phase_stack(self.config) # contains phase instances (potentially with phase specific data)
		
		self._init_game(self.config) # builds maps/objects
		
		self._in_progress = True
		
		return self._step(player)
	
	def _step(self, player, action=None, key=None):  # returns python objs (but json readable)
		
		try:
			
			if not len(self.phase_stack):
				raise GameOver
			
			if self.active_players is None:
				raise NoActiveGameError('Call reset() first')
			
			if action is not None:
				if player not in self.active_players:
					return self._compose_msg(player)
				
				if key is None or key != self.keys[player]:
					raise InvalidKeyError
				
				action = self.active_players[player].verify(action)
			
			# start transaction
			self.begin()
			
			# prepare executing acitons
			
			# execute action
			while len(self.phase_stack):
				phase = self.phase_stack.pop()
				try:
					phase.execute(self, player=self.players[player], action=action)
					# get next action
					out = phase.encode(self)
				except PhaseComplete as intr:
					if not intr.transfer_action():
						action = None
				except PhaseInterrupt as intr:
					if intr.stacks():
						self.phase_stack.append(phase)  # keep current phase around
					new = intr.get_phase()
					if new in self._phases:
						new = self.create_phase(new, **intr.get_phase_kwargs())
					self.phase_stack.append(new)
					if not intr.transfer_action():
						action = None
				else:
					self.phase_stack.append(phase)
					break
			
			if not len(self.phase_stack):
				raise GameOver
		
		except GameOver:
			self.commit()
			
			if self.end_info is None:
				self._images.clear()
				self.end_info = self._end_game()
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
			
			self.active_players = out
			self._images.clear()
			
			msg = self._compose_msg(player)
		
		return msg
	
	######################
	# Must be Overridden
	######################
	
	# This function is implemented by dev to initialize the gamestate, and define player order
	def _init_game(self, config):
		raise NotImplementedError
	
	def _end_game(self): # return info to be sent at the end of the game
		raise NotImplementedError
	
	def _select_player(self):
		raise NotImplementedError
		
	# must be implemented to define initial phase sequence
	def _set_phase_stack(self, config):  # should be in reverse order (returns a tlist stack)
		return tlist()
	
	######################
	# Optionally Overridden
	######################
	
	def _load_config(self):
		config = tdict()
		
		for name, path in self.config_files.items():
			config[name] = containerify(yaml.load(open(path, 'r')))
		
		return config
	
	def _pre_setup(self, config): # allows adjusting the registry after loading the config
		return
	
	def _gen_key(self, player=None):
		key = hex(self._key_rng.getrandbits(64))
		if player is not None:
			self.keys[player] = key
		return key
	
	def _compose_msg(self, player):
		
		if self.end_info is not None:
			# game is already over
			msg = {
				'end': jsonify(self.end_info),
				'table': self.table.pull(), # full table
			}
		
		else:
			
			if player in self.active_players:
				msg = self.active_players[player].pull()
				msg['key'] = self._gen_key(player)
			else:
				msg = {'waiting_for': list(self.active_players.keys())}
			
			msg['players'] = self.players.pull(player)
			msg['table'] = self.table.pull(player)
			
		log = self.log.pull(player)
		if len(log):
			msg['log'] = log
		
		self._images[player] = json.dumps(msg)
		
		return msg
	
	######################
	# Dev functions (return obj)
	######################
	
	def create_phase(self, name, *args, **kwargs):
		return self._phases[name](*args, **kwargs)
	
	def create_object(self, obj_type, **spec): # this should delegate right away, all logic in GameTable
		return self.table.create(obj_type=obj_type, **spec)
	
	######################
	# User functions (return json str)
	######################
	
	def step(self, player, action=None, key=None):  # returns json bytes (str)
		return json.dumps(self._step(player=player, action=action, key=key))
	
	def reset(self, player, seed=None):
		return json.dumps(self._reset(player, seed))
	
	def get_status(self, player):
		
		if player not in self._images:
			self._compose_msg(player)
		
		return self._images[player]
	
	def get_player(self, player):
		return json.dumps(obj_jsonify(self.players[player]))
	
	def get_players(self):
		return json.dumps(self.players.names())
	
	def get_table(self, player=None):
		return json.dumps(self.table.pull(player))
	
	def get_obj_types(self):
		return json.dumps(self.table.get_obj_types())
	
	def get_log(self, player):
		return json.dumps(self.log.get_full(player))
	
	def get_UI_spec(self): # returns a specification for gUsIm - may be overridden to include extra data
		raise NotImplementedError # TODO: by default it should return contents of a config file
	
	def save(self):  # returns string
		return str(Savable.pack(self))
	
	def load(self, data):
		
		obj = Savable.unpack(eval(data))
		
		# load registries
		self._phases = obj._phases
		self.players = obj.players
		self.config_files = obj.config_files
		
		# unpack tmembers
		for mem in self._tmembers:
			self.__dict__[mem] = obj.__dict__[mem]
		
		self.name = obj.name
		self._in_transaction = obj._in_transaction
		self._in_progress = obj._in_progress
		self.DEBUG = obj.DEBUG
	
	
	
	
	



