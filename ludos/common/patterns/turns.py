
from humpack import pack_member, unpack_member
from ludos import tdict, tlist, tset
from ludos.core import GameStack, GamePhase


class TurnPhaseStack(GameStack): # tracks turn counter, inc when creating a TurnPhase
	
	def __init__(self):
		super().__init__()
		self.players = None
		self.counter = None
		self.turn_phases = tset()
		
	def __pack__(self):
		data = super().__pack__()
		
		data['players'] = pack_member(self.players)
		data['counter'] = pack_member(self.counter)
		data['turn_phases'] = pack_member(self.turn_phases)
		
		return data
		
	def __unpack__(self, data):
		
		TurnPhaseStack.__init__(self)
		
		self.players = unpack_member(data['players'])
		self.counter = unpack_member(data['counter'])
		self.turn_phases = unpack_member(data['turn_phases'])
		
		super().__unpack__(data)
		
	def populate(self, phases):
		super().populate(phases)
		for name, info in self._phases.items():
			if issubclass(info.cls, TurnPhase):
				self.turn_phases.add(name)
		
	def reset(self, ctrl):
		self.counter = 0
		self.set_player_order(ctrl.manager)
		super().reset(ctrl)
		
	def set_player_order(self, players):
		self.players = players
	
	def _process_turn(self, name, **kwargs):
		if 'player' not in kwargs and self.players is not None:
			n = self.players[self.counter % len(self.players)].name
			c = self.counter
			kwargs['player'] = self.players[self.counter % len(self.players)]
			self.counter += 1
		return kwargs
	
	def create(self, name, **kwargs):
		if name in self.turn_phases:
			kwargs = self._process_turn(name, **kwargs)
		return super().create(name, **kwargs)


class TurnPhase(GamePhase, req_stack=TurnPhaseStack):
	def __init__(self, player, **info):
		super().__init__(**info)
		self.player = player











