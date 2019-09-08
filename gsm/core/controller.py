
import sys, os
import random
import traceback

from ..containers import tdict, tset, tlist
from .actions import InvalidAction
from .phase import GamePhase
from .logging import GameLogger
from .table import GameTable
from ..control_flow import create_gamestate
from ..mixins import Named, Typed
from ..signals import PhaseComplete, PhaseInterrupt, GameOver

# TODO: include a RNG directly in the controller?

class GameController(tdict):
	
	def __init__(self, debug=False):
		super().__init__()
		self.phases = tdict()
		self.state = None
		self.log = None
		self.table = None
		self.players = tset()
		
		self.DEBUG = debug
	
	def register_players(self, *players):
		self.players.update(players)
	def register_obj_type(self, cls, name=None):
		self.table.register_obj_type(cls, name=name)
	
	def reset(self, player, seed=None):
		
		if seed is None:
			seed = random.getrandbits(64)
		
		self.seed = seed
		random.seed(seed)
		
		self.end_info = None
		self.state = tdict()
		self.log = GameLogger(tlist(p.name for p in self.players))
		self.table = GameTable(tlist(p.name for p in self.players))
		
		self.seq_ptr = 0
		self.phase_stack = self._phase_sequence()
		
		self.active_players = self._init_game() # returns output like step
		return self._format_response(player)
	
	# must be implemented to define initial phase sequence - usually ending in End Phase
	def _set_phase_stack(self):
		return tlist()
	
	# This function is implemented by dev to initialize the gamestate and return the game phase sequence
	def _init_game(self): # set phase_stack (with instances of phases), returns output like step
		raise NotImplementedError
	
	def _end_game(self): # return info to be sent at the end of the game
		raise NotImplementedError
	
	def step(self, player, action=None): # returns json bytes (str)
		
		pass
	
	def _step(self, player, action=None): # returns python objs
		
		if not len(self.phase_stack):
			raise GameOver
		
		# check validity of player
		assert self.active_players is not None, 'No players are set to active'
		
		if player not in self.active_players:
			pass # send waiting_for msg
		
		# check validity of action
		if not self.active_players[player].verify(action):
			raise InvalidAction(action)
		
		# start transaction
		self.begin()
		
		# prepare executing acitons
		
		try:
		
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
			msg = out.pull()
			msg['info'] = out.get_info()
			msg['table'] = self.table.pull()
		
		return msg
	
	def get_table(self, player):
		raise NotImplementedError
	
	def get_log(self, player):
		return self.log.get_full(player)
	
	def create_object(self, obj_type, visible=None, ID=None, **props):
		
		
		
		pass # use table
	
	def save(self):
		raise NotImplementedError
	
	def _save(self):
		pass
	
	def load(self):
		raise NotImplementedError
	
	def _load(self):
		pass



