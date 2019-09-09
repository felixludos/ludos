
import sys, os
import json
import random
import traceback

from ..containers import tdict, tset, tlist
from .actions import InvalidAction
from .phase import GamePhase
from .logging import GameLogger
from .table import GameTable
from ..control_flow import create_gamestate
from ..mixins import Named, Typed
from ..signals import PhaseComplete, PhaseInterrupt, GameOver, ClosedRegistryError, MissingType

# TODO: include a RNG directly in the controller?

class GameController(tdict):
	
	def __init__(self, debug=False):
		super().__init__()
		self.__dict__['_phases'] = {} # dict of phase classes
		
		self.state = None
		self.log = None
		self.table = None
		self.active_players = None
		self.phase_stack = None
		self.players = tset()
		self.in_progress = False
		
		self.DEBUG = debug
	
	def register_obj_type(self, cls=None, name=None):
		if self.in_progress:
			raise ClosedRegistryError
		self.table.register_obj_type(cls=cls, name=name)
	def register_phase(self, cls, name=None):
		if self.in_progress:
			raise ClosedRegistryError
		if name is None:
			name = cls.__class__.__name__
		self._phases[name] = cls
		
	def __getstate__(self):
		data = {}
		
		data['in_progress'] = self.in_progress
		data['DEBUG'] = self.DEBUG
		
		if self.state is not None:
			data['state'] = self.state.__getstate__()
		
		if self.log is not None:
			data['log'] = self.log.__getstate__()
		
		if self.table is not None:
			data['table'] = self.table.__getstate__()
		
		if self.phase_stack is not None:
			data['phase_stack'] = self.phase_stack.__getstate__()
			
		
	
	def reset(self, player, seed=None):
		return json.dumps(self._reset(player, seed))
		
	def _reset(self, player, seed=None):
		
		if seed is None:
			seed = random.getrandbits(64)
		
		self.seed = seed
		random.seed(seed)
		
		self.end_info = None
		self.state = tdict()
		self.log = GameLogger(tlist(p.name for p in self.players))
		self.table = GameTable(tlist(p.name for p in self.players))
		
		self.phase_stack = self._set_phase_stack() # contains phase instances (potentially with phase specific data)
		
		self.active_players = self._init_game() # returns output like step
		
		self.in_progress = True
		
		self.current = None
		
		return self._step(player)
	
	# must be implemented
	def _create_players(self):
		raise NotImplementedError
	
	# must be implemented to define initial phase sequence - usually ending in End Phase
	def _set_phase_stack(self):
		return tlist()
	
	# This function is implemented by dev to initialize the gamestate and return the game phase sequence
	def _init_game(self): # set phase_stack (with instances of phases), returns output like step
		raise NotImplementedError
	
	def _end_game(self): # return info to be sent at the end of the game
		raise NotImplementedError
	
	def step(self, player, action=None): # returns json bytes (str)
		return json.dumps(self._step(player, action))
	
	def _step(self, player, action=None): # returns python objs
		
		try:
			
			if not len(self.phase_stack):
				raise GameOver
			
			# check validity of player
			assert self.active_players is not None, 'No players are set to active'
			
			if player not in self.active_players:
				pass  # send waiting_for msg
			
			# check validity of action
			if not self.active_players[player].verify(action):
				raise InvalidAction(action)
			
			# start transaction
			self.begin()
			
			# prepare executing acitons
		
			# execute action
			while len(self.phase_stack):
				phase = self.phase_stack.pop()
				try:
					phase.execute(self, action, player)
				except PhaseComplete:
					pass
				except PhaseInterrupt as intr:
					self.phase_stack.append(intr.get_phase())
				else:
					self.phase_stack.append(phase)
					break
					
			if not len(self.phase_stack):
				raise GameOver
			
			# get next action
			out = self.phase_stack[-1].encode(self)
			
		except GameOver:
			
			if self.end_info is None:
				self.end_info = self._end_game()
				
			msg = {
				'end': self.end_info,
			}
			
		except Exception as e:
			self.abort()
			# error handling
			
			msg = {
				'error': {
					'type': e.__class__.__name__,
					'msg': traceback.format_exception(*sys.exc_info()),
				}
			}
			
		else:
			self.commit()
			# format output message
			msg = {}
			
			if player in out:
				msg = out[player].pull()
			else:
				msg = {'waiting_for': list(out.keys())}
			
			msg['table'] = self.table.pull()
		
		return msg
	
	def _get_phase(self, name):
		return self._phases[name]
	
	def get_table(self, player):
		raise NotImplementedError
	
	def get_log(self, player):
		return self.log.get_full(player)
	
	def create_object(self, obj_type, visible=None, ID=None, **props):
		return self.table.create(obj_type, visible=visible, ID=ID, **props)
	
	def save(self):
		return json.dumps(self.__getstate__())
	
	def __getstate__(self):
		
		data = {}
		
		data['phases'] = list(self._phases.keys())
		data['state'] = super().__getstate__()
		
		return data
	
	def load(self, data):
		self.__setstate__(json.loads(data))
	
	def __setstate__(self, state):
		
		for name in state['phases']:
			if name not in self._phases:
				raise MissingType(self, name)
			
		super().__setstate__(state['state'])



