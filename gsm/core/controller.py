
import sys
import json
import random
import traceback
import yaml

from ..basic_containers import tdict, tset, tlist
from .logging import GameLogger
from .object import GameObject
from ..mixins import Named, Transactionable, Savable
from ..signals import PhaseComplete, PhaseInterrupt, GameOver, ClosedRegistryError, MissingTypeError, MissingValueError, MissingObjectError
from ..util import unjsonify, Player

class GameController(Named, Transactionable, Savable):
	
	def __new__(cls, *args, **kwargs):
		new = super().__new__(cls)
		
		# meta values (neither for dev nor user) (not including soft registries - they dont change)
		new._tmembers = {'state', 'log', 'table', 'active_players', 'phase_stack',}
		return new
	
	def __init__(self, name=None, debug=False):
		if name is None:
			# TODO: add suggestion about game name
			name = self.__class__.__name__
		super().__init__(name)
		
		# Hard registries - include python classes (cant directly be saved)
		self._phases = tdict() # dict of phase classes
		self._obj_types = tdict() # obj_type classes
		
		# Soft registries - only information, but must be provided before game start
		self.players = tdict()
		self.config_files = tdict()
		self.obj_reqs = tdict()
		
		# GameState
		self._in_progress = False # flag for registration to end
		self._in_transaction = False # flag for transactionable
		self.DEBUG = debug # flag for dev to use as needed
		
		self.state = None
		self.active_players = None
		self.phase_stack = None # should only contain instances of GamePhase
		
		# Game components
		self.log = None
		self.table = None # needed to register obj_types
	
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
		self._in_transaction = True
	
	def abort(self):
		if not self.in_transaction():
			return
		
		for mem in self._tmembers:
			self.__dict__[mem].abort()
		self._in_transaction = True
	
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		# registries
		data['_phases'] = pack(self._phases)
		data['_obj_types'] = pack(self._obj_types)
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
		self._obj_types = unpack(data['_obj_types'])
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
	def register_obj_type(self, cls=None, name=None, required=None, visible=None):
		if self._in_progress:
			raise ClosedRegistryError
		if cls is None:
			assert name is not None, 'Must provide either a name or class'
			cls = GameObject
		elif name is None:
			name = cls.__class__.__name__
		self._obj_types[name] = {'cls':cls,
		                        'reqs':required,  # props required for creating object
		                        'visible':visible}  # props visible to all players always (regardless of obj.visible)
	def register_phase(self, cls, name=None):
		if self._in_progress:
			raise ClosedRegistryError
		if name is None:
			name = cls.__class__.__name__
		self._phases[name] = cls
	def register_player(self, name, **props):
		if self._in_progress:
			raise ClosedRegistryError
		self.players.append(Player(name, **props))
	
	def reset(self, player, seed=None):
		return json.dumps(self._reset(player, seed))
		
	def _reset(self, player, seed=None):
		
		if seed is None:
			seed = random.getrandbits(64)
		
		self.seed = seed
		random.seed(seed)
		
		config = self._load_config()
		
		self.end_info = None
		self.active_players = None
		
		self.state = tdict()
		self.log = GameLogger(tlist(p.name for p in self.players))
		self.table.reset(tlist(p.name for p in self.players))
		
		self.phase_stack = self._set_phase_stack(config) # contains phase instances (potentially with phase specific data)
		
		self._init_game(config) # builds maps/objects
		
		self._in_progress = True
		
		return self._step(player)
	
	def _load_config(self):
		config = tdict()
		
		for name, path in self.config_files.items():
			config[name] = unjsonify(yaml.load(open(path, 'r')))
			
		return config
	
	# must be implemented to define initial phase sequence
	def _set_phase_stack(self, config): # should be in reverse order (returns a tlist stack)
		return tlist()
	
	# This function is implemented by dev to initialize the gamestate
	def _init_game(self, config):
		raise NotImplementedError
	
	def _end_game(self): # return info to be sent at the end of the game
		raise NotImplementedError
	
	def step(self, player, action=None): # returns json bytes (str)
		return json.dumps(self._step(player, action))
	
	def _step(self, player, action=None): # returns python objs
		
		player = self.get_player(player)
		
		try:
			
			if not len(self.phase_stack):
				raise GameOver
			
			if self.active_players is not None:
				
				if player not in self.active_players:
					return {
						'waiting_for': list(self.active_players.keys()),
						'table': self.table.pull(player),
					}
				
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
			
			if self.end_info is None:
				self.end_info = self._end_game()
				
			msg = {
				'end': self.end_info,
				'table': self.table.pull(),
			}
			
		except Exception as e:
			self.abort()
			# error handling
			
			msg = {
				'error': {
					'type': e.__class__.__name__,
					'msg': ''.join(traceback.format_exception(*sys.exc_info())),
				},
				'table': self.table.pull(player),
			}
			
		else:
			self.commit()
			# format output message
			msg = {}
			
			if player in out:
				msg = out[player].pull()
			else:
				msg = {'waiting_for': list(out.keys())}
			
			msg['table'] = self.table.pull(player)
			
			self.active_players = out
			
		return msg
	
	def _get_phase(self, name):
		return self._phases[name]
	
	def get_table(self, player=None):
		return self.table.pull(player)
	
	def get_types(self):
		return self._obj_types.keys()
	
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
		
		if isinstance(obj_type, GameObject):
			pass
		elif obj_type in self._obj_types:
			pass
		else:
			raise MissingObjectError(obj_type)
		
		info = self._get_type(obj_type)
		
		obj = self._create(info.cls, visible=visible, ID=ID, **props)
		self._verify(info.reqs, obj)
		
		if visible is None:  # by default visible to all players
			visible = tset(self.players)
		
		if ID is None:
			ID = self.ID_counter
			self.ID_counter += 1
		
		obj = info.cls(ID=ID, obj_type=obj_type, visible=visible, _table=self.table, **props)
		
		self.table.update(obj._id, obj)
		
		return obj
	
	def _get_type_info(self, obj_type):
		if obj_type not in self.obj_types:
			raise MissingObjectError(obj_type)
		return self._obj_types[obj_type]
	
	def _verify(self, reqs, obj):  # check that all requirements for a gameobject are satisfied
		if reqs is not None:
			for req in reqs:
				if req not in obj:
					raise MissingValueError(obj.get_type(), req, *reqs)
	
	def save(self): # returns string
		return json.dumps(self.__getstate__())
	
	def __getstate__(self):
		
		data = {}
		
		# registered items
		data['phases'] = list(self._phases.keys())
		data['obj_types'] = list(self._obj_types.keys())
		
		# handle GameTable carefully to load registered GameObject types
		
		data['state'] = super().__getstate__()
		
		return data
		
		data = {}
		
		data['in_progress'] = self._in_progress
		data['DEBUG'] = self.DEBUG
		
		if self.state is not None:
			data['state'] = self.state.__getstate__()
		
		if self.log is not None:
			data['log'] = self.log.__getstate__()
		
		if self.table is not None:
			data['table'] = self.table.__getstate__()
		
		if self.phase_stack is not None:
			data['phase_stack'] = self.phase_stack.__getstate__()
	
	def load(self, data):
		self.__setstate__(json.loads(data))
	
	def __setstate__(self, state):
		
		for obj_type in state['obj_types']:
			if obj_type not in self.obj_types:
				raise MissingTypeError(self, obj_type)
		
		for name in state['phases']:
			if name not in self._phases:
				raise MissingType(self, name)
			
		# take special care when handling table
		
		super().__setstate__(state['state'])



