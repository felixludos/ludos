
import sys
import json
import random
import traceback
import yaml

from ..basic_containers import tdict, tset, tlist, containerify
from .logging import GameLogger
from .object import GameObject
from .state import GameState
from .table import GameTable
from ..mixins import Named, Transactionable, Savable
from ..signals import PhaseComplete, PhaseInterrupt, GameOver, InvalidKeyError, ClosedRegistryError, MissingTypeError, MissingValueError, MissingObjectError
from ..util import Player, RandomGenerator

class GameController(Named, Transactionable, Savable):
	
	def __new__(cls, *args, **kwargs):
		new = super().__new__(cls)
		
		# meta values (neither for dev nor user) (not including soft registries - they dont change)
		new._tmembers = {'state', 'log', 'table', 'active_players', 'phase_stack', 'keys', 'RNG', '_images'}
		return new
	
	def __init__(self, name=None, debug=False):
		if name is None:
			# TODO: add suggestion about game name
			name = self.__class__.__name__
		super().__init__(name)
		
		# Hard registries - include python classes (cant directly be saved)
		self._phases = tdict() # dict of phase classes
		
		# Soft registries - only information, but must be provided before game start
		self.players = tdict()
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
		self.phase_stack = None # should only contain instances of GamePhase
		
		# Game components
		self.log = None
		self.table = GameTable() # needed to register obj_types
	
	def begin(self):
		if self.in_transaction():
			self.commit()
			
		for mem in self._tmembers:
			self.__dict__[mem].begin()
		self._in_transaction = True
	
	def in_transaction(self):
		return self._in_transaction
	
	def commit(self):
		if not self.in_transaction():
			return
		
		for mem in self._tmembers:
			self.__dict__[mem].commit()
		self._in_transaction = False
	
	def abort(self):
		if not self.in_transaction():
			return
		
		for mem in self._tmembers:
			self.__dict__[mem].abort()
		self._in_transaction = False
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		# registries
		data['_phases'] = pack(self._phases)
		data['players'] = pack(self.players)
		data['config_files'] = pack(self.config_files)
		
		# tmembers - arbitrary Savable instances
		for mem in self._tmembers:
			data[mem] = pack(self.__dict__[mem])
		
		data['name'] = self.name
		
		return data
	
	@classmethod
	def __load(cls, data):
		self = cls()
		unpack = cls.__unpack
		
		# load registries
		self._phases = unpack(data['_phases'])
		self.players = unpack(data['players'])
		self.config_files = unpack(data['config_files'])
		
		# unpack tmembers
		for mem in self._tmembers:
			self.__dict__[mem] = data[mem]
			
		self.name = data['name']
		
		return self
		
	def register_config(self, name, path):
		if self._in_progress:
			raise ClosedRegistryError
		self.config_files[name] = path
	def register_obj_type(self, cls=None, name=None):
		if self._in_progress:
			raise ClosedRegistryError
		self.table.register_obj_type(cls=cls, name=name)
	def register_phase(self, cls, name=None):
		if self._in_progress:
			raise ClosedRegistryError
		if name is None:
			name = cls.__class__.__name__
		self._phases[name] = cls
	def register_player(self, name, **props):
		if self._in_progress:
			raise ClosedRegistryError
		self.players[name] = Player(name, **props)
	
	def reset(self, seed=None):
		return json.dumps(self._reset(seed))
		
		
	def _reset(self, seed=None):
		
		if seed is None:
			seed = random.getrandbits(64)
		
		self.seed = seed
		self.RNG = RandomGenerator(self.seed)
		
		config = self._load_config()
		
		self.end_info = None
		self.active_players = None
		
		self.state = GameState()
		self.log = GameLogger(tset(p.name for p in self.players))
		self.table.reset(tset(p.name for p in self.players))
		
		self.phase_stack = self._set_phase_stack(config) # contains phase instances (potentially with phase specific data)
		
		self._init_game(config) # builds maps/objects
		
		self._in_progress = True
		
		player = self._select_player()
		
		return self._step(player)
	
	def _load_config(self):
		config = tdict()
		
		for name, path in self.config_files.items():
			config[name] = containerify(yaml.load(open(path, 'r')))
			
		return config
	
	# must be implemented to define initial phase sequence
	def _set_phase_stack(self, config): # should be in reverse order (returns a tlist stack)
		return tlist()
	
	# This function is implemented by dev to initialize the gamestate, and define player order
	def _init_game(self, config):
		raise NotImplementedError
	
	def _end_game(self): # return info to be sent at the end of the game
		raise NotImplementedError
	
	def _select_player(self):
		raise NotImplementedError
	
	def step(self, player, action=None, key=None): # returns json bytes (str)
		return json.dumps(self._step(player=player, action=action))
	
	def _step(self, player, action=None, key=None): # returns python objs (but json readable)
		
		try:
			
			if not len(self.phase_stack):
				raise GameOver
			
			if action is not None and (key is None or key != self.keys[player]):
				raise InvalidKeyError
			
			if self.active_players is not None:
				
				if player not in self.active_players:
					return self._compose_msg(player)
				
				# check validity of action
				action = self.active_players[player].verify(action)
			
			else:
				assert action is None, 'there shouldnt be an action if the game hasnt started'
			
			# start transaction
			self.begin()
			
			# prepare executing acitons
		
			# execute action
			while len(self.phase_stack):
				phase = self.phase_stack.pop()
				try:
					phase.execute(self, player=player, action=action)
					# get next action
					out = phase.encode(self)
				except PhaseComplete:
					pass
				except PhaseInterrupt as intr:
					if intr.stacks():
						self.phase_stack.append(phase) # keep current phase around
					new = intr.get_phase()
					if new in self._phases:
						new = self._get_phase(new)()
					self.phase_stack.append(new)
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
	
	def _gen_key(self, player=None):
		key = hex(self.RNG.getrandbits(64))
		if player is not None:
			self.keys[player] = key
		return key
	
	def _compose_msg(self, player):
		
		if self.end_info is not None:
			# game is already over
			msg = {
				'end': self.end_info,
				'table': self.table.pull(), # full table
			}
		
		else:
			
			if player in self.active_players:
				msg = self.active_players[player].pull()
				msg['key'] = self._gen_key(player)
			else:
				msg = {'waiting_for': list(self.active_players.keys())}
			
			msg['table'] = self.table.pull(player)
		
		self._images[player] = json.dumps(msg)
		
		return msg
	
	def _get_phase(self, name):
		return self._phases[name]
	
	def get_table(self, player=None):
		return self.table.pull(player)
	
	def get_obj_types(self):
		return self.table.get_obj_types()
	
	def get_status(self, player):
		
		if player not in self._images:
			self._compose_msg(player)
		
		return self._images[player]
	
	def get_log(self, player):
		return self.log.get_full(player)
	
	def get_UI_spec(self): # returns a specification for gUsIm - may be overridden to include extra data
		raise NotImplementedError # TODO: by default it should return contents of a config file
	
	def get_player(self, name):
		for p in self.players:
			if p.name == name:
				return p
	def get_players(self):
		return tlist(p.name for p in self.players)
	
	def create_object(self, obj_type, visible=None, ID=None, **props):
		return self.table.create(obj_type=obj_type, visible=visible, ID=ID, **props)
	
	def save(self): # returns string
		return json.dumps(self.__save())
	
	@classmethod
	def load(self, data):
		return self.__load(json.loads(data))
	



